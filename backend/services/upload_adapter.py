"""
Compatibility adapter so you can call `parse_document(path)` no matter
what the underlying parser exposes. Adjust the import below if your
parser lives elsewhere.
"""
from __future__ import annotations
import os
import importlib
from typing import Any, Dict

# If you moved the file, change this path:
parser = importlib.import_module("services.upload_parser")

CANDIDATE_PARSE_FUNCS = [
    "parse_document", "parse_file", "process_file",
    "handle_upload", "extract_and_validate",
]

def _try(name: str, path: str):
    fn = getattr(parser, name, None)
    return fn(path) if callable(fn) else None

def parse_document(path: str) -> Dict[str, Any]:
    fn = getattr(parser, "parse_document", None)
    if callable(fn):
        return fn(path)

    for name in CANDIDATE_PARSE_FUNCS:
        if name == "parse_document":
            continue
        out = _try(name, path)
        if out is None:
            continue
        if isinstance(out, dict):
            out.setdefault("ext", os.path.splitext(path)[1].lstrip(".").lower())
            return out
        return {"text": str(out), "ext": os.path.splitext(path)[1].lstrip(".").lower()}

    # Fallback: minimal shape
    return {"ext": os.path.splitext(path)[1].lstrip(".").lower()}
