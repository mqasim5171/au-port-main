# services/adapter.py
"""
Compatibility adapter for parsing documents.
Ensures we can always call `adapter.parse_document(path)` safely,
even if the underlying parser uses a different function name.
"""

import os
import importlib
from typing import Any, Dict

# Import your lightweight parser (upload_parser.py)
parser = importlib.import_module("services.upload_parser")

CANDIDATE_FUNCS = [
    "parse_document", "parse_file", "process_file",
    "handle_upload", "extract_and_validate",
]


def _try(name: str, path: str):
    fn = getattr(parser, name, None)
    return fn(path) if callable(fn) else None


def parse_document(path: str) -> Dict[str, Any]:
    """Try all candidate parse functions until one works.
    Always return a dict with at least {"ext": file_extension}.
    """
    fn = getattr(parser, "parse_document", None)
    if callable(fn):
        return fn(path)

    for name in CANDIDATE_FUNCS:
        if name == "parse_document":
            continue
        out = _try(name, path)
        if out is None:
            continue
        if isinstance(out, dict):
            out.setdefault("ext", os.path.splitext(path)[1].lstrip(".").lower())
            return out
        return {"text": str(out), "ext": os.path.splitext(path)[1].lstrip(".").lower()}

    # Fallback
    return {"ext": os.path.splitext(path)[1].lstrip(".").lower()}
