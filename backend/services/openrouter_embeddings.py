from dotenv import load_dotenv
load_dotenv()

import os
import time
import json
import hashlib
import requests
from typing import List, Dict, Any, Optional

OPENROUTER_EMBED_URL = "https://openrouter.ai/api/v1/embeddings"

def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()

def _get_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()

def _get_embed_model() -> str:
    # ✅ embedding model (NOT chat model)
    return os.getenv("OPENROUTER_EMBED_MODEL", "qwen/qwen3-embedding-4b").strip()

def embed_texts(
    texts: List[str],
    model: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Returns:
      {
        "vectors": List[List[float]],
        "meta": {model, latency_ms, hashes}
      }
    """
    api_key = _get_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing (env not loaded)")

    used_model = model or _get_embed_model()

    clean = [(t or "").strip() for t in texts]
    hashes = [sha256(t) for t in clean]

    payload = {
        "model": used_model,
        "input": clean,
    }

    t0 = time.time()
    r = requests.post(
        OPENROUTER_EMBED_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "Air QA Portal"),
        },
        data=json.dumps(payload),
        timeout=timeout,
    )
    latency_ms = int((time.time() - t0) * 1000)

    if r.status_code >= 400:
        raise RuntimeError(f"OpenRouter embeddings error {r.status_code}: {r.text[:800]}")

    data = r.json()

    # OpenAI-compatible: data["data"] is list with {"embedding": [...]}
    items = data.get("data") or []
    vectors = [it.get("embedding") for it in items]
    if not vectors or any(v is None for v in vectors):
        raise RuntimeError(f"Embeddings response malformed: {str(data)[:800]}")

    return {
        "vectors": vectors,
        "meta": {
            "model": used_model,
            "latency_ms": latency_ms,
            "hashes": hashes,
        },
    }
  