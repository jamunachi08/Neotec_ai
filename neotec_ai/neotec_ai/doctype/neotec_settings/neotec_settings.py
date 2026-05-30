import frappe
from frappe.model.document import Document


class NeotecSettings(Document):
    def validate(self):
        if self.temperature is not None and not (0 <= self.temperature <= 2):
            frappe.throw("Temperature must be between 0 and 2.")
        if self.max_rows_per_query and self.max_rows_per_query < 1:
            frappe.throw("Max Rows Per Query must be at least 1.")
