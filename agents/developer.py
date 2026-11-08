"""Developer: writes website changes for one task."""
from .base import Agent
from .tooling import run_tool

ROLE = """You are the Developer agent for the Fieldline Run Club website (plain HTML, CSS and JavaScript).
Every page shares the same header, menu and footer. Keep the existing style and structure.
Make the smallest change that completes the task. Never add secrets, tracking or external scripts.
Always reply with JSON in the exact format you are asked for."""


class Developer(Agent):
    name = "developer"
    role = ROLE
    tools = ["list_files", "read_file", "write_file"]

    def edit_site(self, task):
        files = run_tool(self, "list_files")["files"]
        choice = self.think(
            f"Task: {task['details']}\nWebsite files: {files}\n"
            'Which ONE file should be changed? Reply with JSON: {"file": "...", "reason": "..."}',
            ["file", "reason"],
        )
        current = run_tool(self, "read_file", path=choice["file"])["content"]
        prompt = (
            f"Task: {task['details']}\nHere is the full current content of {choice['file']}:\n\n{current}\n\n"
            'Reply with JSON: {"summary": "...", "content": "<the FULL new file content>"}'
        )
        for attempt in range(2):
            change = self.think(prompt, ["summary", "content"])
            result = run_tool(self, "write_file", path=choice["file"], content=change["content"])
            if result["ok"]:
                return {"ok": True, "file": choice["file"], "summary": change["summary"]}
            prompt = f"The file failed its check: {result['error']}. Fix it and reply in the same JSON format."
        return {"ok": False, "file": choice["file"], "error": result["error"]}
