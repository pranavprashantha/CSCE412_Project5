"""Test Engineer: writes new test cases for the website and runs the test suite."""
import json

from .base import Agent
from .tooling import run_tool

ROLE = """You are the Test Engineer agent for a static website (Fieldline Run Club).
You write test cases that are checked against the real HTML files before every deploy.

Each test checks that one page contains some exact text. Only use text that is really in the
page you were shown, copied exactly (for example a heading, a nav link, an element id, or a
data attribute). Focus on things that would break the site if they went missing.

Reply with JSON:
{"reasoning": "...", "tests": [{"name": "...", "file": "events.html", "must_contain": ["...", "..."]}]}
Write between 5 and 10 tests."""


class TestEngineer(Agent):
    name = "test_engineer"
    role = ROLE
    tools = ["list_files", "read_file", "save_tests", "run_tests"]

    def write_tests(self, requirements):
        # read every page so the tests are based on the real files
        files = run_tool(self, "list_files")["files"]
        pages = ""
        for path in files:
            if path.endswith(".html"):
                content = run_tool(self, "read_file", path=path)["content"]
                pages += "\n\n===== " + path.replace("website/", "") + " =====\n" + content

        reply = self.think("Requirements:\n" + requirements + "\n\nPages:" + pages, ["reasoning", "tests"])

        saved = run_tool(self, "save_tests", tests=reply["tests"])
        results = run_tool(self, "run_tests")
        return {"ok": results["exit_code"] == 0, "saved": saved["saved"], "dropped": saved["dropped"],
                "passed": results["passed"], "total": results["total"], "failed": results["failed"]}

    def explain_results(self):
        # run the tests and explain any failures in plain words
        results = run_tool(self, "run_tests")
        if results["exit_code"] == 0:
            return {"ok": True, "summary": "all " + str(results["total"]) + " tests passed"}
        reply = self.think("These tests failed:\n" + json.dumps(results["failed"]) +
                           '\nReply with JSON: {"summary": "...", "likely_cause": "...", "fix": "..."}',
                           ["summary", "likely_cause", "fix"])
        return {"ok": False, "summary": reply["summary"], "likely_cause": reply["likely_cause"], "fix": reply["fix"]}