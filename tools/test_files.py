"""test_files.py - the Test Engineer's tools: save tests and run the test suite.

Tests are saved as JSON in tests/generated/agent_tests.json, and run by
tests/run_tests.py (the same script the pipeline runs).
"""
import json
import os
import subprocess
import sys

from common import ROOT

TEST_FILE = os.path.join(ROOT, "tests", "generated", "agent_tests.json")


def save_tests(tests):
    # only keep tests that are filled in correctly and pass on the current site
    kept = []
    dropped = []
    for t in tests:
        path = os.path.join(ROOT, "website", t.get("file", ""))
        if not t.get("name") or not t.get("must_contain") or not os.path.isfile(path):
            dropped.append({"test": t, "reason": "missing name, must_contain, or the file does not exist"})
            continue
        html = open(path, encoding="utf-8").read()
        missing = []
        for text in t["must_contain"]:
            if text not in html:
                missing.append(text)
        if missing:
            dropped.append({"test": t["name"], "reason": "text not on the page now: " + ", ".join(missing)})
            continue
        kept.append({"name": t["name"], "file": t["file"], "must_contain": t["must_contain"]})

    os.makedirs(os.path.dirname(TEST_FILE), exist_ok=True)
    json.dump(kept, open(TEST_FILE, "w"), indent=2)
    return {"saved": len(kept), "dropped": dropped, "path": "tests/generated/agent_tests.json"}


def run_tests():
    # run the same tests the pipeline runs and return the results
    subprocess.run([sys.executable, "tests/make_version.py"], cwd=ROOT, capture_output=True)
    result = subprocess.run([sys.executable, "tests/run_tests.py"], cwd=ROOT, capture_output=True, text=True)
    report = json.load(open(os.path.join(ROOT, "reports", "test-results.json")))
    failed = []
    for r in report["results"]:
        if not r["passed"]:
            failed.append(r)
    return {"exit_code": result.returncode, "passed": report["passed"], "total": report["total"], "failed": failed}