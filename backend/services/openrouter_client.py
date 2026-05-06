from dotenv import load_dotenv
load_dotenv()

import os, time, json, hashlib, re
import requests
from typing import Dict, Any, Optional, Tuple

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"

def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()

def _get_key() -> str:
    # read env at runtime (not import-time)
    return os.getenv("OPENROUTER_API_KEY", "").strip()

def _get_model() -> str:
    return os.getenv("OPENROUTER_MODEL", "mistralai/mistral-small-24b-instruct-2501").strip()

def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()

    # try direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # try fenced json
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return json.loads(m.group(1))

    # fallback: first {...}
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
        raise RuntimeError("OPENROUTER_API_KEY missing (env not loaded)")

    used_model = model or _get_model()

    payload = {
        "model": used_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": user
                + "\n\nReturn ONLY valid JSON. No markdown.\n\nJSON_SCHEMA_HINT:\n"
                + schema_hint
            },
        ],
    }

    t0 = time.time()
    r = requests.post(
        OPENROUTER_BASE,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # OpenRouter recommends these (not always required, but good)
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "Air QA Portal"),
        },
        data=json.dumps(payload),
        timeout=120,
    )

    latency_ms = int((time.time() - t0) * 1000)

    if r.status_code >= 400:
        # 401 "User not found" => almost always bad/invalid key
        raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text[:800]}")

    data = r.json()
    content = data["choices"][0]["message"]["content"]

    parsed = _extract_json(content)

    meta = {
        "raw_response": content,
        "model": used_model,
        "latency_ms": latency_ms,
        "input_hash": sha256(user),
    }
    return parsed, meta
