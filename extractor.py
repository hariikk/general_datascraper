"""
extractor.py — call the configured LLM backend and parse structured output.

Two backends behind one interface:
  - "ollama": POST /api/generate with a JSON schema ("format"), which is what
    forces the local model to return a clean table instead of prose.
  - "openai":  POST /chat/completions on any OpenAI-compatible endpoint
    (KI connect NRW, Gemini-compatible gateways, etc.) with JSON mode.

The FIELDS list in config.py is turned into the schema + prompt automatically,
so you never hand-write JSON schema.
"""

import json
import re

import requests

import config


def build_schema(fields):
    properties = {}
    for entry in fields:
        name, kind = entry[0], entry[1]
        if kind == "number":
            properties[name] = {"type": "integer"}
        elif kind == "choice":
            properties[name] = {"type": "string", "enum": entry[2]}
        else:  # "text"
            properties[name] = {"type": "string"}
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": properties,
            "required": [e[0] for e in fields],
        },
    }


def _field_prompt(fields):
    lines = []
    for entry in fields:
        name, kind = entry[0], entry[1]
        if kind == "number":
            lines.append(f'  - "{name}": a whole number')
        elif kind == "choice":
            lines.append(f'  - "{name}": one of {", ".join(entry[2])}')
        else:
            lines.append(f'  - "{name}": short text (use the exact value stated in the paper)')
    return "\n".join(lines)


def _build_prompt(text, instruction, fields):
    base = (
        instruction.strip()
        + "\n\nFor each entry, return a JSON object with exactly these fields:\n"
        + _field_prompt(fields)
        + "\n\n"
    )
    if config.LLM_BACKEND == "openai":
        # OpenAI JSON mode requires a top-level OBJECT, so wrap the array.
        base += 'Return ONLY a JSON object with a single key "items" whose value is '
        base += 'the array of entries. If nothing qualifies, return {"items": []}.'
    else:
        base += "Return ONLY a JSON array (no prose, no markdown fences). "
        base += "If nothing qualifies, return []."
    return base + "\n\nTEXT:\n" + text


def backend_status():
    """Return {ok, message, model} for the configured backend (never exits).

    The web app calls this to show a friendly "Ollama not installed" error instead
    of crashing. The CLI's check_backend() wraps it with a SystemExit.
    """
    if config.LLM_BACKEND == "openai":
        if not config.OPENAI_BASE_URL or not config.OPENAI_MODEL:
            return {
                "ok": False,
                "message": "OpenAI backend not configured. Set OPENAI_BASE_URL / OPENAI_MODEL in config.py.",
                "model": config.OPENAI_MODEL,
            }
        return {
            "ok": True,
            "message": f"OpenAI backend ready ({config.OPENAI_MODEL})",
            "model": config.OPENAI_MODEL,
        }

    model = config.OLLAMA_MODEL
    try:
        r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
    except Exception:
        return {
            "ok": False,
            "message": "Ollama is not installed or not running. Install it from ollama.com, start it, then try again.",
            "model": model,
        }

    models = [m.get("name", "") for m in r.json().get("models", [])]
    found = any(
        m == model or m.split(":")[0] == model.split(":")[0]
        for m in models
    )
    if not found:
        return {
            "ok": False,
            "message": f"Ollama is running, but the model '{model}' is not installed. Run:  ollama pull {model}",
            "model": model,
        }
    return {"ok": True, "message": f"Ollama ready ({model})", "model": model}


def check_backend():
    """CLI entry point: exit with a friendly message if the backend is unreachable."""
    status = backend_status()
    if not status["ok"]:
        raise SystemExit(status["message"])


def extract(text, fields=None, instruction=None):
    """Extract records from `text`.

    `fields` and `instruction` override config.FIELDS / config.INSTRUCTION, so the
    web app can pass user-defined columns + a user-written goal at runtime.
    """
    fields = list(fields) if fields else list(config.FIELDS)
    instruction = instruction or config.INSTRUCTION
    text = text[: config.MAX_CHARS] if len(text) > config.MAX_CHARS else text
    prompt = _build_prompt(text, instruction, fields)
    if config.LLM_BACKEND == "openai":
        raw = _call_openai(prompt)
    else:
        raw = _call_ollama(prompt, fields)
    return _parse_response(raw)


def _call_ollama(prompt, fields):
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": build_schema(fields),
        "options": {
            "temperature": config.TEMPERATURE,
            "num_ctx": config.NUM_CTX,
            "num_predict": config.NUM_PREDICT,
        },
    }
    r = requests.post(f"{config.OLLAMA_URL}/api/generate", json=payload, timeout=900)
    r.raise_for_status()
    return r.json().get("response", "")


def _call_openai(prompt):
    payload = {
        "model": config.OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.TEMPERATURE,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}
    url = config.OPENAI_BASE_URL.rstrip("/") + "/chat/completions"
    r = requests.post(url, json=payload, headers=headers, timeout=900)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _parse_response(raw):
    def _load(s):
        try:
            d = json.loads(s)
        except json.JSONDecodeError:
            return None
        if isinstance(d, list):
            return d
        if isinstance(d, dict) and isinstance(d.get("items"), list):
            return d["items"]
        return None

    got = _load(raw)
    if got is not None:
        return got

    # fallback: JSON wrapped in ```json ... ``` fences
    m = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        got = _load(m.group(1))
        if got is not None:
            return got

    # fallback: first [...] anywhere in the text
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if m:
        got = _load(m.group(0))
        if got is not None:
            return got

    return []  # gave up — treat as "nothing extracted"
