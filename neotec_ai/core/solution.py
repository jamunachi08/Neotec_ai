"""Answers a question directly. Tries to ground the answer in ERPNext data
via the safe query layer; if that isn't possible, answers in prose."""

import json
import frappe
from neotec_ai.llm import client as llm
from neotec_ai.core.render import render
from neotec_ai.core import reporting

DEFAULT_SOLUTION_PROMPT = (
    "You are an ERPNext operations assistant. Answer the user's question "
    "clearly and concisely. If data is provided, base your answer on it. "
    "If data is empty or irrelevant, answer from general business knowledge "
    "and say so.\n\nQUESTION: {question}\n\nDATA (JSON):\n{data}"
)


def _resolve(settings):
    name = frappe.db.get_value(
        "Neotec Prompt Template",
        {"template_type": "Solution", "enabled": 1}, "name",
    )
    if name:
        tpl = frappe.get_doc("Neotec Prompt Template", name)
        if tpl.content:
            return tpl.content
    return DEFAULT_SOLUTION_PROMPT


def answer(question, settings):
    rows = []
    plan = None
    try:
        plan = reporting.generate_query_plan(question, settings)
        rows = reporting.execute_query_plan(plan, settings)
    except Exception:
        rows = []  # answer without data grounding
    prompt = render(_resolve(settings), question=question,
                    data=json.dumps(rows, default=str)[:8000])
    text = llm.chat([{"role": "user", "content": prompt}], settings=settings)
    return {"answer": text, "plan": plan, "data": rows}
