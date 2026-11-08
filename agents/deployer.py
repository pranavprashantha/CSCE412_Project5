"""Deployer: publishes the website to AWS and applies approved fixes."""
from .base import Agent
from .tooling import run_tool

ROLE = """You are the Deployer agent. You publish a static website to an S3 bucket behind CloudFront.
You will be shown the output of a dry run (what would be uploaded or deleted).
Decide whether it is safe to deploy. Uploads of changed site files are normal.
Deleting files is risky: set "needs_approval" to true if anything would be deleted.
Reply with JSON: {"decision": "deploy" or "stop", "needs_approval": true/false, "reason": "..."}"""


class Deployer(Agent):
    name = "deployer"
    role = ROLE
    tools = ["deploy_dryrun", "deploy", "apply_fix"]

    def deploy(self, task, approve):
        dryrun = run_tool(self, "deploy_dryrun")
        decision = self.think(f"Task: {task['details']}\nDry run output:\n{dryrun['output']}",
                              ["decision", "needs_approval", "reason"])
        if decision["decision"] != "deploy":
            return {"ok": False, "stopped": decision["reason"]}
        # Plain-code rule on top of the AI decision: deletions always need a human.
        if decision["needs_approval"] or "delete:" in dryrun["output"]:
            if not approve("Deploy will delete files from S3", dryrun["output"]):
                return {"ok": False, "stopped": "human rejected the deletion"}
        result = run_tool(self, "deploy")
        return {"ok": result["exit_code"] == 0, "output": result["output"][-500:]}

    def apply_fix(self, fix):
        result = run_tool(self, "apply_fix", fix=fix)
        return {"ok": bool(result.get("ok")), "result": result}
