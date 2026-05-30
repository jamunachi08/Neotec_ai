import frappe
from neotec_ai.core.reporting import DEFAULT_QUERY_PROMPT
from neotec_ai.core.advisory import DEFAULT_ADVISORY_PROMPT
from neotec_ai.core.intent import DEFAULT_INTENT_PROMPT
from neotec_ai.core.solution import DEFAULT_SOLUTION_PROMPT
from neotec_ai.core.dashboard import DEFAULT_DASHBOARD_PROMPT


def after_install():
    _seed("Default Query Plan", "Query", DEFAULT_QUERY_PROMPT,
          "Converts a question into a safe query plan.")
    _seed("Default Advisory Report", "Advisory", DEFAULT_ADVISORY_PROMPT,
          "Writes the management report with advice & directions.")
    _seed("Default Intent Classifier", "Intent", DEFAULT_INTENT_PROMPT,
          "Decides solution vs report vs dashboard.")
    _seed("Default Solution Answer", "Solution", DEFAULT_SOLUTION_PROMPT,
          "Answers a question directly, grounded in data.")
    _seed("Default Dashboard Designer", "Dashboard", DEFAULT_DASHBOARD_PROMPT,
          "Designs dashboard chart widgets from data.")
    frappe.db.commit()


def _seed(title, ttype, content, desc):
    if frappe.db.exists("Neotec Prompt Template", title):
        return
    frappe.get_doc({
        "doctype": "Neotec Prompt Template",
        "title": title, "template_type": ttype,
        "enabled": 1, "description": desc, "content": content,
    }).insert(ignore_permissions=True)
