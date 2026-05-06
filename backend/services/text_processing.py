# services/text_processing.py
import os
import tempfile
from typing import Dict, Optional, Union
from services import adapter  # your adapter import; adapter.parse_document(path) required

def parse_path(path: str) -> Dict:
    """Parse a file path using the adapter; returns dict with at least 'ext' and maybe 'text'."""
    return adapter.parse_document(path)

def parse_bytes(file_bytes: bytes, filename: str) -> Dict:
    """
    Save bytes to a temp file and call adapter.parse_document on it.
    Returns the adapter output dict (text, ext, pages etc).
    """
    ext = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        tmp_path = tmp.name
    try:
        return adapter.parse_document(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def extract_text_from_path_or_bytes(path_or_bytes: Union[str, bytes], filename: Optional[str] = None) -> str:
    """
    Convenience function: if path_or_bytes is a str it's a path; if bytes, it's raw bytes.
    Returns the extracted text (or empty string).
    """
    out = {}
    if isinstance(path_or_bytes, str):
        out = parse_path(path_or_bytes)
    else:
        if filename is None:
            raise ValueError("filename is required when passing bytes")
        out = parse_bytes(path_or_bytes, filename)
    return (out.get("text") or "").strip()
