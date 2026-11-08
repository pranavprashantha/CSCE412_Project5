"""common.py - small helpers shared by the tools."""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def settings():
    with open(os.path.join(ROOT, "config", "settings.json")) as f:
        return json.load(f)


def aws(*args):
    """Run an AWS CLI command as the project5-agent user. Returns (ok, output)."""
    cmd = ["aws", *args, "--profile", settings()["aws_profile"], "--output", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    return result.returncode == 0, output
