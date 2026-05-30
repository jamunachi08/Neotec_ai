"""Generates a dashboard: the model proposes 1-4 widgets, each with its own
SAFE query plan. Each plan is executed through the same permission-aware
layer, then shaped into chart-ready data for Frappe Charts."""

import json
import frappe
from neotec_ai.llm import client as llm
from neotec_ai.core.render import render
from neotec_ai.core import reporting

DEFAULT_DASHBOARD_PROMPT = (
    "Design a dashboard for the request. Return ONLY valid JSON:\n"
    '{"title": "<dashboard title>", "widgets": [\n'
    '  {"title": "<widget title>", "chart_type": "bar|line|pie|percentage",\n'
    '   "label_field": "<field for x-axis/labels>",\n'
    '   "value_field": "<numeric field or aggregate alias>",\n'
    '   "query_plan": {"doctype": "<DocType>", '
    '"fields": ["<label_field>", "<value expression as value_field>"], '
    '"filters": {}, "group_by": "<field or null>", '
    '"order_by": "<field desc or null>", "limit": 12}}\n'
    "]}\n"
    "Use only the schema below. Max 4 widgets. Use aggregates like "
    "'sum(grand_total) as total' where useful.\n\n"
    "SCHEMA:\n{schema}\n\nTODAY: {today}\n\nREQUEST: {question}"
)


def _resolve(settings):
    name = frappe.db.get_value(
        "Neotec Prompt Template",
        {"template_type": "Dashboard", "enabled": 1}, "name",
    )
    if name:
        tpl = frappe.get_doc("Neotec Prompt Template", name)
        if tpl.content:
            return tpl.content
    return DEFAULT_DASHBOARD_PROMPT


def generate(question, settings):
    schema = reporting.build_schema_context(settings)
    prompt = render(_resolve(settings), schema=schema,
                    question=question, today=frappe.utils.today())
    raw = llm.chat([{"role": "user", "content": prompt}],
                   settings=settings, json_mode=True)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError:
        frappe.throw(f"The model did not return a valid dashboard spec:\n{raw[:500]}")

    widgets_out = []
    for w in (spec.get("widgets") or [])[:4]:
        try:
            rows = reporting.execute_query_plan(w.get("query_plan") or {}, settings)
        except Exception as e:
            widgets_out.append({"title": w.get("title", "Widget"),
                                "error": str(e), "chart_type": w.get("chart_type")})
            continue
        lf, vf = w.get("label_field"), w.get("value_field")
        labels = [str(r.get(lf, "")) for r in rows] if lf else []
        values = [r.get(vf, 0) for r in rows] if vf else []
        widgets_out.append({
            "title": w.get("title", "Widget"),
            "chart_type": w.get("chart_type", "bar"),
            "labels": labels, "values": values, "data": rows,
        })
    return {"title": spec.get("title", "Dashboard"), "widgets": widgets_out}
