"""package_logs.py - turns my real run logs into the submission folder.

It only sorts and reformats lines from the .jsonl run logs. Nothing is written by hand.

Usage:
    python3 tools/package_logs.py --goal-run evidence/<goal run>.jsonl \
        --failure-run evidence/<failure run>.jsonl
"""
import argparse
import json
import os
import re
import shutil

OUT = "project5-agent-logs"
SECRET = re.compile(r"AKIA[0-9A-Z]{16}|AQ\.[A-Za-z0-9_\-]{20,}|aws_secret_access_key\S*")


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def redact(text):
    return SECRET.sub("[REDACTED]", text)


def line(e):
    return redact(f"{e['time']}  [{e['kind']}] {e['agent']}\n{json.dumps(e['data'], indent=2)}\n")


def write(name, entries, title):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(f"# {title}\n# {len(entries)} events, in time order\n\n")
        for e in entries:
            f.write(line(e) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--goal-run", required=True)
    p.add_argument("--failure-run", required=True)
    a = p.parse_args()

    goal, fail = load(a.goal_run), load(a.failure_run)
    both = goal + fail
    os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)

    # 1. one file per agent (goal run + failure run)
    for i, agent in enumerate(["planner", "developer", "deployer", "validator"], 1):
        mine = [e for e in both if e["agent"] == agent]
        write(f"0{i}-{agent}-agent.log", mine, f"{agent} agent: inputs, LLM decisions, tool runs")

    # 2. every agent-to-agent message
    messages = [e for e in both if e["kind"] == "message"]
    with open(os.path.join(OUT, "05-agent-communication.json"), "w") as f:
        f.write(redact(json.dumps(messages, indent=2)))

    # 3. every tool run, with args and results
    write("06-tool-execution.log", [e for e in both if e["kind"] == "tool run"], "tool runs: tool, args, result")

    # 4. the whole failure run, start to finish
    write("07-failure-recovery.log", fail, "failure and recovery run (bucket policy deleted)")

    # untouched copies of the original logs
    for src in (a.goal_run, a.failure_run):
        with open(src) as f, open(os.path.join(OUT, "raw", os.path.basename(src)), "w") as g:
            g.write(redact(f.read()))

    readme = os.path.join(os.path.dirname(__file__), "logs-README.txt")
    if os.path.exists(readme):
        shutil.copy(readme, os.path.join(OUT, "README.txt"))

    shutil.make_archive(OUT, "zip", ".", OUT)
    print(f"Made {OUT}/ and {OUT}.zip")


if __name__ == "__main__":
    main()
