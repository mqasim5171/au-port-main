from dotenv import load_dotenv
load_dotenv()

import os
import time
import json
import hashlib
import re
import requests
from typing import Dict, Any, Optional, Tuple

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _get_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def _get_model() -> str:
    return os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if m:
        return json.loads(m.group(1))

    m2 = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m2:
        return json.loads(m2.group(1))

    raise ValueError("Model did not return valid JSON.")


def call_openrouter_json(
    system: str,
    user: str,
    schema_hint: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    api_key = _get_key()

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing. Please check backend/.env")

    used_model = model or _get_model()

    payload = {
        "model": used_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    user
                    + "\n\nReturn ONLY valid JSON. No markdown.\n\nJSON_SCHEMA_HINT:\n"
                    + schema_hint
                ),
            },
        ],
    }

    input_chars = len(user or "")
    print(
        f"[OPENROUTER] Starting request | model={used_model} | input_chars={input_chars}",
        flush=True,
    )

    t0 = time.time()

    try:
        r = requests.post(
            OPENROUTER_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "Air QA Portal"),
            },
            data=json.dumps(payload),
            timeout=45,
        )
    except requests.exceptions.Timeout:
        latency_ms = int((time.time() - t0) * 1000)
        print(
            f"[OPENROUTER] Timeout after {latency_ms}ms | model={used_model}",
            flush=True,
        )
        raise RuntimeError(
            "OpenRouter request timed out. Free models can be slow or overloaded. Try again or reduce submission text."
        )
    except requests.exceptions.RequestException as e:
        latency_ms = int((time.time() - t0) * 1000)
        print(
            f"[OPENROUTER] Network error after {latency_ms}ms | error={str(e)}",
            flush=True,
        )
        raise RuntimeError(f"OpenRouter network error: {str(e)}")

    latency_ms = int((time.time() - t0) * 1000)

    print(
        f"[OPENROUTER] Response received | status={r.status_code} | latency_ms={latency_ms}",
        flush=True,
    )

    if r.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text[:800]}")

    data = r.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"OpenRouter returned unexpected response: {str(data)[:800]}")

    parsed = _extract_json(content)

    meta = {
        "raw_response": content,
        "model": used_model,
        "latency_ms": latency_ms,
        "input_hash": sha256(user),
    }

    print(
        f"[OPENROUTER] JSON parsed successfully | latency_ms={latency_ms}",
        flush=True,
    )

    return parsed, meta