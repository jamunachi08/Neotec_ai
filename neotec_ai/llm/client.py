"""Config-driven LLM client. Talks to any OpenAI-compatible endpoint
(Ollama, vLLM, LM Studio, etc.). Nothing about the model or endpoint is
hardcoded — it all comes from the 'Neotec Settings' single DocType."""

import json
import requests
import frappe


def get_settings():
    settings = frappe.get_single("Neotec Settings")
    if not settings.enabled:
        frappe.throw("Neotec AI is disabled. Enable it in Neotec Settings.")
    if not settings.api_base_url or not settings.model:
        frappe.throw("Configure API Base URL and Model in Neotec Settings.")
    return settings


def chat(messages, settings=None, json_mode=False):
    """Send a chat-completion request and return the assistant text."""
    settings = settings or get_settings()
    url = settings.api_base_url.rstrip("/") + "/chat/completions"

    headers = {"Content-Type": "application/json"}
    api_key = settings.get_password("api_key") if settings.api_key else None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": settings.model,
        "messages": messages,
        "temperature": settings.temperature or 0.2,
        "max_tokens": settings.max_tokens or 2000,
    }
    if json_mode:
        # Most OpenAI-compatible servers honour this; harmless if ignored.
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = requests.post(
            url, headers=headers, data=json.dumps(payload),
            timeout=settings.request_timeout or 120,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        frappe.throw(f"Could not reach the LLM at {url}: {e}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        frappe.throw(f"Unexpected LLM response: {json.dumps(data)[:500]}")
