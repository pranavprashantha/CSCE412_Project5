"""site_files.py - the Developer's tools: list, read and write website files.

Writes are only allowed inside website/ and config/, and every file is
checked before it is saved (HTML must parse, JSON must be valid).
"""
import json
import os
from html.parser import HTMLParser

from common import ROOT

ALLOWED = [os.path.join(ROOT, "website"), os.path.join(ROOT, "config")]


def _safe_path(path):
    full = os.path.realpath(os.path.join(ROOT, path))
    if not any(full == a or full.startswith(a + os.sep) for a in ALLOWED):
        raise PermissionError(f"{path} is outside website/ and config/")
    return full


def list_files():
    out = []
    for folder, _, files in os.walk(os.path.join(ROOT, "website")):
        for name in files:
            out.append(os.path.relpath(os.path.join(folder, name), ROOT))
    return sorted(out)


def read_file(path):
    with open(_safe_path(path)) as f:
        return f.read()


def check(path, content):
    """Return an error message, or "" if the file looks valid."""
    if path.endswith(".json"):
        try:
            json.loads(content)
        except json.JSONDecodeError as error:
            return f"invalid JSON: {error}"
    if path.endswith(".html"):
        lower = content.lower()
        if "<html" not in lower or "</html>" not in lower:
            return "HTML is missing <html> or </html>"
        try:
            HTMLParser().feed(content)
        except Exception as error:
            return f"HTML could not be parsed: {error}"
    return ""


def write_file(path, content):
    full = _safe_path(path)
    problem = check(path, content)
    if problem:
        return {"ok": False, "path": path, "error": problem}
    with open(full, "w") as f:
        f.write(content)
    return {"ok": True, "path": path, "bytes": len(content)}
