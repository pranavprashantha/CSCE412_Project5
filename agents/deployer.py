"""Deployer: publishes the website to AWS and applies approved fixes."""
from .base import Agent
from .tooling import run_tool
import json

ROLE = """You are the Deployer agent. You publish a static website to an S3 bucket behind CloudFront.
You will be shown the output of a dry run (what would be uploaded or deleted).
Decide whether it is safe to deploy. Uploads of changed site files are normal.
Deleting files is risky: set "needs_approval" to true if anything would be deleted.
Reply with JSON: {"decision": "deploy" or "stop", "needs_approval": true/false, "reason": "..."}

You also review the CI/CD pipeline setup. A correct pipeline runs Source -> Build -> Deploy -> Verify,
triggers on the main branch, runs the tests before anything is deployed, and passes the tested files
(the build artifact) to Deploy and Verify."""

EXPECTED_ORDER = ["Source", "Build", "Deploy", "Verify"]


class Deployer(Agent):
    name = "deployer"
    role = ROLE
    tools = ["deploy_dryrun", "deploy", "apply_fix", "pipeline_config"]

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
    
    def check_pipeline(self):
        config = run_tool(self, "pipeline_config")
        if "error" in config:
            return {"ok": False, "error": config["error"]}

        # Plain-code checks
        problems = []
        order = [s["stage"] for s in config["stages"]]
        if order != EXPECTED_ORDER:
            problems.append("stage order is " + str(order) + ", expected " + str(EXPECTED_ORDER))
        stage_var = {"Build": "test", "Deploy": "deploy", "Verify": "verify"}
        for s in config["stages"]:
            if s["stage"] == "Source" and s["branch"] != "main":
                problems.append("Source is not watching the main branch")
            if s["stage"] in stage_var and stage_var[s["stage"]] not in s["env_vars"]:
                problems.append(s["stage"] + " does not set STAGE=" + stage_var[s["stage"]])
            if s["stage"] in ("Deploy", "Verify") and "BuildArtifact" not in s["inputs"]:
                problems.append(s["stage"] + " does not use the tested BuildArtifact")

        # AI review of the same config
        review = self.think(
            "Pipeline config:\n" + json.dumps(config, indent=2) +
            '\nReview it. Reply with JSON: {"looks_correct": true/false, "issues": ["..."], "suggestions": ["..."]}',
            ["looks_correct", "issues", "suggestions"],
        )
        # Plain-code rule: ok comes from the checks, the AI adds comments.
        return {"ok": len(problems) == 0, "problems": problems, "review": review}
