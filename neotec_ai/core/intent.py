"""Classifies a user query into one of: solution | report | dashboard.
The classifier prompt is an editable Neotec Prompt Template."""

import frappe
from neotec_ai.llm import client as llm
from neotec_ai.core.render import render

VALID = {"solution", "report", "dashboard"}

DEFAULT_INTENT_PROMPT = (
    "Classify the user request into exactly one word: solution, report, or "
    "dashboard.\n"
    "- 'solution' = a direct answer or recommendation to a question.\n"
    "- 'report' = a tabular/written report of data.\n"
    "- 'dashboard' = charts / visual KPIs.\n"
    "Reply with ONLY the single word.\n\nREQUEST: {question}"
)


def _resolve(settings):
    name = frappe.db.get_value(
        "Neotec Prompt Template",
        {"template_type": "Intent", "enabled": 1}, "name",
    )
    if name:
        tpl = frappe.get_doc("Neotec Prompt Template", name)
        if tpl.content:
            return tpl.content
    return DEFAULT_INTENT_PROMPT


def classify(question, settings):
    prompt = render(_resolve(settings), question=question)
    raw = llm.chat([{"role": "user", "content": prompt}], settings=settings)
    word = (raw or "").strip().lower().split()[0] if raw.strip() else "solution"
    word = "".join(c for c in word if c.isalpha())
    return word if word in VALID else "solution"
