"""tooling.py - how agents run tools.

Each agent has an allow-list. run_tool refuses any tool not on that list,
runs the real script or function, and logs the result as a "tool run".
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)

import site_files  # noqa: E402  (Developer's file tools)


def _script(cmd, timeout=180):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=timeout)
    return {"exit_code": result.returncode, "output": (result.stdout + result.stderr).strip()}


def _verify():
    result = _script([sys.executable, os.path.join(TOOLS, "verify.py")])
    try:
        return {"exit_code": result["exit_code"], "report": json.loads(result["output"])}
    except json.JSONDecodeError:
        return result


def _inspect():
    result = _script([sys.executable, os.path.join(TOOLS, "aws_inspect.py")])
    try:
        return json.loads(result["output"])
    except json.JSONDecodeError:
        return result


def _json_script(cmd):
    result = _script(cmd)
    try:
        return json.loads(result["output"])
    except json.JSONDecodeError:
        return result


REGISTRY = {
    "list_files": lambda: {"files": site_files.list_files()},
    "read_file": lambda path: {"path": path, "content": site_files.read_file(path)},
    "write_file": lambda path, content: site_files.write_file(path, content),
    "deploy_dryrun": lambda: _script(["bash", os.path.join(TOOLS, "deploy.sh"), "dryrun"]),
    "deploy": lambda: _script(["bash", os.path.join(TOOLS, "deploy.sh"), "deploy"]),
    "verify": _verify,
    "aws_inspect": _inspect,
    "apply_fix": lambda fix: _json_script([sys.executable, os.path.join(TOOLS, "apply_fix.py"), fix]),
}


def run_tool(agent, tool, **args):
    if tool not in agent.tools:
        agent.log.write(agent.name, "tool run", {"tool": tool, "refused": "not on this agent's allow-list"})
        raise PermissionError(f"{agent.name} is not allowed to use {tool}")
    result = REGISTRY[tool](**args)
    shown = {k: v for k, v in args.items() if k != "content"}  # don't copy whole files into the log
    agent.log.write(agent.name, "tool run", {"tool": tool, "args": shown, "result": _short(result)})
    return result


def _short(value, limit=1500):
    text = json.dumps(value)
    return value if len(text) <= limit else text[:limit] + "...(cut)"
