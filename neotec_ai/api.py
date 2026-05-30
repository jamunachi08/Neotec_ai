"""Whitelisted entry points the Neotec Console calls. Each orchestrates a
flow and writes an audit record to Neotec Operation Log."""

import json
import time
import frappe
from frappe.utils import now_datetime
from neotec_ai.llm import client as llm
from neotec_ai.core import reporting, advisory, intent, solution, dashboard


def _log(op_type, status, request="", plan=None, summary="", error="", model="", ms=0):
    try:
        settings = frappe.get_single("Neotec Settings")
        if not settings.log_all_operations:
            return
        frappe.get_doc({
            "doctype": "Neotec Operation Log",
            "operation_type": op_type, "status": status,
            "user": frappe.session.user, "model_used": model,
            "duration_ms": ms, "request": request,
            "generated_plan": json.dumps(plan, default=str) if plan else "",
            "result_summary": summary, "error": error,
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(title="Neotec AI: failed to write operation log")


@frappe.whitelist()
def test_connection():
    start = time.time()
    settings = llm.get_settings()
    try:
        reply = llm.chat([{"role": "user", "content": "Reply with: OK"}], settings=settings)
        ms = int((time.time() - start) * 1000)
        _log("Connection Test", "Success", summary=reply[:200], model=settings.model, ms=ms)
        return {"ok": True, "model": settings.model, "reply": reply.strip()}
    except Exception as e:
        _log("Connection Test", "Error", error=str(e), model=settings.model)
        raise


@frappe.whitelist()
def ask(query, mode=None):
    """Single entry point for the console. Routes to solution / report /
    dashboard. `mode` forces a route; otherwise the intent is classified."""
    start = time.time()
    settings = llm.get_settings()
    chosen = (mode or "").lower().strip() or None
    plan = None
    try:
        if chosen not in ("solution", "report", "dashboard"):
            chosen = intent.classify(query, settings)

        if chosen == "report":
            plan = reporting.generate_query_plan(query, settings)
            rows = reporting.execute_query_plan(plan, settings)
            report = advisory.generate_management_report(query, rows, settings) \
                if settings.enable_advisory else ""
            payload = {"intent": "report", "plan": plan,
                       "row_count": len(rows), "data": rows, "report": report}
            summary = f"report, {len(rows)} rows"

        elif chosen == "dashboard":
            dash = dashboard.generate(query, settings)
            payload = {"intent": "dashboard", "dashboard": dash}
            summary = f"dashboard, {len(dash.get('widgets', []))} widgets"

        else:  # solution
            sol = solution.answer(query, settings)
            plan = sol.get("plan")
            payload = {"intent": "solution", "answer": sol["answer"],
                       "plan": plan, "data": sol["data"]}
            summary = "solution"

        ms = int((time.time() - start) * 1000)
        _log(chosen.capitalize(), "Success", request=query, plan=plan,
             summary=summary, model=settings.model, ms=ms)
        payload["ok"] = True
        payload["question"] = query
        return payload

    except frappe.ValidationError as e:
        _log("Report", "Blocked", request=query, plan=plan, error=str(e), model=settings.model)
        raise
    except Exception as e:
        _log("Report", "Error", request=query, plan=plan, error=str(e), model=settings.model)
        raise


@frappe.whitelist()
def save_result(payload):
    """Persist a console result permanently as a Neotec Saved Report."""
    data = json.loads(payload) if isinstance(payload, str) else payload
    doc = frappe.get_doc({
        "doctype": "Neotec Saved Report",
        "title": data.get("title") or (data.get("question") or "Untitled")[:120],
        "result_type": (data.get("intent") or "Solution").capitalize(),
        "question": data.get("question"),
        "owner_user": frappe.session.user,
        "created_on": now_datetime(),
        "report_content": data.get("report") or data.get("answer") or "",
        "data_snapshot": json.dumps(data.get("data") or [], default=str),
        "dashboard_spec": json.dumps(data.get("dashboard") or {}, default=str),
        "query_plan": json.dumps(data.get("plan") or {}, default=str),
    }).insert()
    return {"ok": True, "name": doc.name}


def _rows_to_matrix(rows):
    if not rows:
        return [["No data"]]
    headers = list(rows[0].keys())
    matrix = [headers]
    for r in rows:
        matrix.append([r.get(h, "") for h in headers])
    return matrix


def _save_file(filename, content, is_private=1):
    f = frappe.get_doc({
        "doctype": "File", "file_name": filename,
        "is_private": is_private, "content": content,
    }).insert(ignore_permissions=True)
    return f.file_url


@frappe.whitelist()
def export_excel(data_json, title="neotec_report"):
    """Build an .xlsx from row data and return a downloadable file URL."""
    from frappe.utils.xlsxutils import make_xlsx
    rows = json.loads(data_json) if isinstance(data_json, str) else data_json
    xlsx = make_xlsx(_rows_to_matrix(rows), "Report")
    content = xlsx.getvalue() if hasattr(xlsx, "getvalue") else xlsx
    url = _save_file(f"{title}.xlsx", content)
    return {"ok": True, "file_url": url}


@frappe.whitelist()
def export_pdf(html, title="neotec_report"):
    """Render provided HTML to a PDF file and return a downloadable URL."""
    from frappe.utils.pdf import get_pdf
    content = get_pdf(html)
    url = _save_file(f"{title}.pdf", content)
    return {"ok": True, "file_url": url}
