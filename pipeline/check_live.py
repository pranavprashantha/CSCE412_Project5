# check_live.py
# Checks the live website after a deploy.
# 1. Runs the 7 checks from Project 5 (tools/verify.py)
# 2. Checks the live version.json is the release we just deployed
# 3. Checks the events filter still works
# Saves the results to reports/verify-results.json and exits 1 if anything failed.
#
# Usage: python3 pipeline/check_live.py <release>

import json
import os
import subprocess
import sys
import urllib.request

SITE = "https://csce412prra2413.me"
release = sys.argv[1]


def get_page(path):
    # returns the status code and the text of a page
    try:
        response = urllib.request.urlopen(SITE + path, timeout=10)
        return response.status, response.read().decode("utf-8")
    except Exception:
        return 0, ""


# 1. Project 5 checks
output = subprocess.run(["python3", "tools/verify.py"], capture_output=True, text=True)
checks = json.loads(output.stdout)["results"]

# 2. Is the right release live?
status, text = get_page("/version.json")
live_release = ""
if status == 200:
    live_release = json.loads(text)["release"]
checks.append({
    "check": "release_matches",
    "passed": live_release == release,
    "evidence": {"expected": release, "live": live_release},
})

# 3. Does the events filter still work?
events_status, events_page = get_page("/events.html")
js_status, js_file = get_page("/js/main.js")
filter_works = events_status == 200 and js_status == 200 and "data-filter=" in events_page and "filters" in js_file
checks.append({
    "check": "events_filter_works",
    "passed": filter_works,
    "evidence": {"events_status": events_status, "main_js_status": js_status},
})

# Count the results
passed = 0
for c in checks:
    if c["passed"]:
        passed += 1
        print("PASS", c["check"])
    else:
        print("FAIL", c["check"], c["evidence"])
print(passed, "/", len(checks), "passed")

# Save the results
os.makedirs("reports", exist_ok=True)
report = {"release": release, "passed": passed, "total": len(checks), "results": checks}
json.dump(report, open("reports/verify-results.json", "w"), indent=2)

if passed < len(checks):
    sys.exit(1)
