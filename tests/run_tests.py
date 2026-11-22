# run_tests.py
# Tests the website files before they get deployed.
# Saves the results to reports/test-results.json
# Exits with 1 if any test fails so the pipeline stops.

import json
import os
import re
import subprocess
import sys

SITE = "website"
PAGES = ["index.html", "about.html", "events.html", "mission.html", "signin.html", "404.html"]
REQUIRED_FILES = PAGES + ["css/style.css", "js/main.js"]

results = []


def add_result(name, passed, detail=""):
    results.append({"test": name, "passed": passed, "detail": detail})


def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def to_file_path(link, page):
    # returns the file a link points to, or None if it's an outside link
    if link.startswith("http") or link.startswith("mailto:") or link.startswith("#"):
        return None
    link = link.split("#")[0]
    if link == "":
        return None
    if link.startswith("/"):
        link = link[1:]
        if link == "":
            link = "index.html"
        return link
    folder = os.path.dirname(page)
    return os.path.normpath(os.path.join(folder, link))


def get_commit():
    # CodeBuild gives us the commit, on my laptop we ask git
    commit = os.environ.get("CODEBUILD_RESOLVED_SOURCE_VERSION")
    if commit:
        return commit
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


# Test 1: required files exist
for f in REQUIRED_FILES:
    add_result("file exists: " + f, os.path.isfile(os.path.join(SITE, f)))

for page in PAGES:
    path = os.path.join(SITE, page)
    if not os.path.isfile(path):
        continue
    html = read_file(path)

    # Test 2: basic page structure
    add_result(page + " has <html lang>", '<html lang="' in html)
    add_result(page + " has a title", re.search(r"<title>.+</title>", html) is not None)
    add_result(page + " has one h1", html.count("<h1") == 1)
    add_result(page + " has nav and footer", "<nav" in html and "<footer" in html)

    # Test 3: internal links go to real pages
    broken = []
    for link in re.findall(r'<a[^>]*href="([^"]+)"', html):
        target = to_file_path(link, page)
        if target and not os.path.isfile(os.path.join(SITE, target)):
            broken.append(link)
    add_result(page + " links work", len(broken) == 0, ", ".join(broken))

    # Test 4: css, js and images exist
    missing = []
    for asset in re.findall(r'(?:src|<link[^>]*href)="([^"]+)"', html):
        target = to_file_path(asset, page)
        if target and not os.path.isfile(os.path.join(SITE, target)):
            missing.append(asset)
    add_result(page + " assets exist", len(missing) == 0, ", ".join(missing))

# Test 5: the main features are still there
events = read_file(os.path.join(SITE, "events.html"))
add_result("events page has filter buttons", events.count("data-filter=") >= 2)
add_result("events page has events", "data-type=" in events)

signin = read_file(os.path.join(SITE, "signin.html"))
add_result("sign in page has the form", 'id="signin-form"' in signin and 'id="email"' in signin and 'id="password"' in signin)

# Test 6: version.json matches the commit
commit = get_commit()
try:
    version = json.load(open(os.path.join(SITE, "version.json")))
    add_result("version.json matches commit", version["release"] == commit, "expected " + commit + ", got " + version["release"])
except Exception as e:
    add_result("version.json matches commit", False, str(e))

# Test 7: tests written by the Test Engineer agent (tests/generated/*.json)
if os.path.isdir("tests/generated"):
    for name in sorted(os.listdir("tests/generated")):
        if not name.endswith(".json"):
            continue
        tests = json.load(open(os.path.join("tests/generated", name)))
        for t in tests:
            path = os.path.join(SITE, t["file"])
            if not os.path.isfile(path):
                add_result("generated: " + t["name"], False, t["file"] + " not found")
                continue
            html = read_file(path)
            missing = [text for text in t.get("must_contain", []) if text not in html]
            add_result("generated: " + t["name"], len(missing) == 0, "missing: " + ", ".join(missing))

# Save and print the results
failed = [r for r in results if not r["passed"]]
report = {
    "release": commit,
    "total": len(results),
    "passed": len(results) - len(failed),
    "failed": len(failed),
    "results": results,
}
os.makedirs("reports", exist_ok=True)
json.dump(report, open("reports/test-results.json", "w"), indent=2)

for r in results:
    if r["passed"]:
        print("PASS", r["test"])
    else:
        print("FAIL", r["test"], "-", r["detail"])
print(report["passed"], "/", report["total"], "passed")

if failed:
    sys.exit(1)
