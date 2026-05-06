# services/clo_parser.py
import re
from typing import List
from docx import Document

def extract_text_from_docx(file_path: str) -> str:
    """Read all text from a Word file (.docx)."""
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extract_clos_from_text(text: str) -> List[str]:
    """Return list of CLO strings found in the text (best-effort)."""
    if not text:
        return []

    t = text.replace("\r", "\n")

    # 1) CLO1: ... patterns
    clo_matches = re.findall(r'CLO\s*\d+[:\-\)]?\s*(.+)', t, flags=re.IGNORECASE)
    if clo_matches:
        return [m.strip() for m in clo_matches if m.strip()]

    # 2) Course Objectives / Learning Outcomes block
    m = re.search(
        r'(Course Objectives|Course Learning Outcomes|Learning Outcomes)[:\s\-]*\n(.{10,5000}?)\n\s*\n',
        t, flags=re.IGNORECASE | re.DOTALL
    )
    if m:
        block = m.group(2)
        lines = []
        for ln in block.splitlines():
            ln = re.sub(r'^[\-\*\d\.\)\(]+\s*', '', ln.strip())
            if len(ln) > 10:
                lines.append(ln)
        if lines:
            return lines

    # 3) fallback: keywords
    lines = []
    for ln in t.splitlines():
        ln_s = re.sub(r'^[\-\*\d\.\)\(]+\s*', '', ln.strip())
        if len(ln_s) < 20:
            continue
        if re.search(r'\b(able to|understand|apply|analyze|design|develop|evaluate|demonstrate)\b',
                     ln_s, flags=re.IGNORECASE):
            lines.append(ln_s)

    # Deduplicate
    seen, out = set(), []
    for l in lines:
        if l not in seen:
            out.append(l); seen.add(l)
    return out
