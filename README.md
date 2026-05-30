# Neotec AI Operator for ERPNext — Version 0.2.0

An "artificial operator" for ERPNext, built as a native Frappe app.
**Everything is configured from the frontend — no features are hardcoded.**
The LLM endpoint, model, all prompts, behaviour, safety caps, and the exact
set of data the AI may read live in editable DocTypes.

Built in stages. Each version is useful on its own and reuses one safety
spine: **whitelist + permissions + audit (+ approval, from V3).**

---

## Version 2 — the Neotec Console (this release)

A single screen (**Awesome Bar → "Neotec Console"**) where the user types a
query and the system decides what to do:

- **Solution** — a direct answer/recommendation, grounded in ERPNext data.
- **Report** — a management report (Summary, Key Findings, Advice &
  Recommendations, Suggested Directions) plus the underlying data table.
- **Dashboard** — auto-generated charts (bar / line / pie / percentage)
  using Frappe Charts.

The route is auto-detected from the query, or you can force it with the
mode selector.

**Every result has actions:**
- **Save permanently** → stored as a `Neotec Saved Report` record.
- **Print** → opens a print view.
- **Export Excel** → `.xlsx` download.
- **Export PDF** → `.pdf` download.

### Still read-only (by design)
V2 reads and advises; it does not create, edit, submit, or approve any
ERPNext document. That is V3+, gated behind human approval.

---

## Version 1 — foundation (included)
- Config-driven connection to a self-hosted open-source LLM (Ollama / vLLM /
  any OpenAI-compatible server).
- Safe query layer: question → structured plan → `frappe.get_list`
  (permissions always enforced) → data. No raw SQL.
- Whitelist of allowed DocTypes; per-query row cap; full audit log.
- Advisory engine that turns data into a management report with advice.

---

## Install

```bash
cd ~/frappe-bench
bench get-app /path/to/neotec_ai
bench --site yoursite install-app neotec_ai
bench --site yoursite migrate
bench build      # picks up the console page assets
```

## Configure (all in the UI — search "Neotec Settings")
1. **LLM Connection** — API Base URL (e.g. `http://localhost:11434/v1`),
   Model (e.g. `qwen2.5:14b-instruct`), API Key (blank for local).
2. **Data Scope** — add the DocTypes the AI may read (Sales Invoice,
   Customer, Item, …).
3. **Behaviour** — advisory on/off, max-rows cap, audit on/off.
4. Prompts are seeded as editable **Neotec Prompt Template** records
   (Query, Advisory, Intent, Solution, Dashboard). Edit freely — nothing is
   fixed in code.

## Use
Open **Neotec Console**, type a query, pick Auto-detect (or a mode), press
**Ask**. Use Save / Print / Export on the result.

---

## Staged roadmap

| Version | Capability | Risk | Gate |
|--------|------------|------|------|
| V1 | Reporting + advice (read-only) | None | — |
| **V2 (this)** | Console: solution / report / dashboard + save/print/export | None | — |
| V3 | Draft creation, then act-with-approval | Low→Med | Human approval |
| V4 | Bounded autonomy: rule-based auto-approve, capped | Higher | Config rules + limits |

> Licensing: builds on GPL-3.0 ERPNext/Frappe, so the app is GPL-3.0. Brand
> and sell services freely; confirm any closed-source plan with a lawyer.
