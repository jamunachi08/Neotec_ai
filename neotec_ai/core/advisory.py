"""Takes the data produced by the reporting layer and writes a management
report that includes analysis, advice, suggestions and directions."""

import json
import frappe
from neotec_ai.llm import client as llm
from neotec_ai.core.render import render


DEFAULT_ADVISORY_PROMPT = (
    "You are a management analyst for a company using ERPNext. "
    "Based on the question and the data, write a concise management report in "
    "Markdown with exactly these sections:\n"
    "## Summary\n## Key Findings\n## Advice & Recommendations\n"
    "## Suggested Directions / Next Steps\n\n"
    "Be specific and base every statement on the data. If the data is "
    "insufficient, say so plainly instead of guessing.\n\n"
    "QUESTION: {question}\n\nDATA (JSON):\n{data}\n\nTODAY: {today}"
)


def _resolve_prompt(settings):
    name = settings.get("advisory_prompt_template")
    if name:
        tpl = frappe.get_doc("Neotec Prompt Template", name)
        if tpl.enabled and tpl.content:
            return tpl.content
    return DEFAULT_ADVISORY_PROMPT


def generate_management_report(question, data, settings):
    template = _resolve_prompt(settings)
    prompt = render(template, question=question,
                    data=json.dumps(data, default=str)[:12000],
                    today=frappe.utils.today())
    return llm.chat([{"role": "user", "content": prompt}], settings=settings)
