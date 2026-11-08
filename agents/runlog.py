"""runlog.py - one log file per run, one JSON line per event.

Every event has a "kind" so the log shows what was AI and what was plain code:
    message       - one agent handing work to another
    LLM decision  - a reply from Gemini
    LLM retry     - Gemini's reply was invalid and was asked again
    tool run      - a script or command that ran, with its result
    approval      - a human approved or rejected a change
"""
import json
import os
from datetime import datetime, timezone

COLORS = {
    "message": "\033[36m",       # cyan
    "LLM decision": "\033[35m",  # magenta
    "LLM retry": "\033[33m",     # yellow
    "tool run": "\033[32m",      # green
    "approval": "\033[34m",      # blue
}
RESET = "\033[0m"


class RunLog:
    def __init__(self, folder="logs"):
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = os.path.join(folder, f"run-{stamp}.jsonl")

    def write(self, agent, kind, data):
        entry = {
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "agent": agent,
            "kind": kind,
            "data": data,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        preview = json.dumps(data)
        if len(preview) > 160:
            preview = preview[:157] + "..."
        print(f"{COLORS.get(kind, '')}[{kind}] {agent}{RESET}: {preview}")
