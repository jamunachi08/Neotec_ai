"""Turns a natural-language question into a SAFE, structured query plan and
executes it through frappe.get_list — which automatically respects the
current user's permissions. No raw SQL is generated in V1, by design."""

import json
import frappe
from neotec_ai.llm import client as llm
from neotec_ai.core.render import render


DEFAULT_QUERY_PROMPT = (
    "You convert a business question into a JSON query plan for an ERPNext "
    "(Frappe) system. Only use the DocTypes and fields listed in the schema. "
    "Return ONLY valid JSON with this shape:\n"
    '{"doctype": "<DocType>", "fields": ["field1", "count(name) as count"], '
    '"filters": {"fieldname": ["operator", value]}, '
    '"group_by": "fieldname or null", "order_by": "fieldname desc or null", '
    '"limit": <int>}\n'
    "Use only read operations. Do not invent field names.\n\n"
    "SCHEMA:\n{schema}\n\nTODAY: {today}\n\nQUESTION: {question}"
)


def get_allowed_doctypes(settings):
    rows = settings.get("allowed_doctypes") or []
    return [r.document_type for r in rows]


def build_schema_context(settings):
    """Describe only the whitelisted DocTypes to the model."""
    lines = []
    for dt in get_allowed_doctypes(settings):
        try:
            meta = frappe.get_meta(dt)
        except Exception:
            continue
        fields = [
            f"{f.fieldname} ({f.fieldtype})"
            for f in meta.fields
            if f.fieldtype not in ("Section Break", "Column Break", "HTML", "Tab Break")
        ]
        lines.append(f"DocType '{dt}': " + ", ".join(fields[:40]))
    return "\n".join(lines) if lines else "No DocTypes whitelisted."


def _resolve_prompt(settings, link_field, default_text):
    name = settings.get(link_field)
    if name:
        tpl = frappe.get_doc("Neotec Prompt Template", name)
        if tpl.enabled and tpl.content:
            return tpl.content
    return default_text


def generate_query_plan(question, settings):
    schema = build_schema_context(settings)
    template = _resolve_prompt(settings, "query_prompt_template", DEFAULT_QUERY_PROMPT)
    prompt = render(template, schema=schema, question=question,
                    today=frappe.utils.today(), data="")
    raw = llm.chat(
        [{"role": "user", "content": prompt}], settings=settings, json_mode=True
    )
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        frappe.throw(f"The model did not return a valid query plan:\n{raw[:500]}")


def execute_query_plan(plan, settings):
    """Run the plan safely. Enforces the whitelist, the row cap, and — via
    frappe.get_list — the current user's read permissions."""
    doctype = plan.get("doctype")
    allowed = get_allowed_doctypes(settings)
    if doctype not in allowed:
        frappe.throw(f"DocType '{doctype}' is not in the allowed list.", title="Blocked")

    cap = settings.max_rows_per_query or 500
    limit = min(int(plan.get("limit") or cap), cap)

    return frappe.get_list(
        doctype,
        fields=plan.get("fields") or ["name"],
        filters=plan.get("filters") or {},
        group_by=plan.get("group_by") or None,
        order_by=plan.get("order_by") or None,
        limit_page_length=limit,
        ignore_permissions=False,  # permissions ALWAYS enforced
    )
