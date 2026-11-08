"""Security/Validator: checks the live site and diagnoses failures."""
import json

from .base import Agent
from .tooling import run_tool

FIXES = {
    "restore_bucket_policy": "Put back the saved S3 bucket policy that lets CloudFront read the files",
    "set_default_root_object": "Set CloudFront's default root object to index.html",
    "set_https_redirect": "Set CloudFront to redirect HTTP to HTTPS",
}

ROLE = f"""You are the Security/Validator agent for a static website served from a private S3 bucket
through CloudFront, with a Route 53 domain and an ACM certificate.

You read check results and AWS settings, then explain them. You never change anything yourself.
When something fails, find the most likely root cause from the evidence, and pick a fix ONLY from
this list (or "none" if no listed fix applies):
{json.dumps(FIXES, indent=2)}

Expected healthy setup: the bucket policy allows cloudfront.amazonaws.com to s3:GetObject;
default root object is index.html; viewer protocol policy is redirect-to-https;
the domain has an A alias record pointing to CloudFront."""


class Validator(Agent):
    name = "validator"
    role = ROLE
    tools = ["verify", "aws_inspect"]

    def verify(self):
        result = run_tool(self, "verify")
        report = result.get("report", result)
        summary = self.think(
            f"Check results:\n{json.dumps(report)}\n"
            'Reply with JSON: {"status": "healthy" or "failing", "summary": "..."}',
            ["status", "summary"],
        )
        failed = [r for r in report.get("results", []) if not r["passed"]] if "results" in report else ["verify crashed"]
        # Plain-code rule: the status comes from the checks, not from the AI's opinion.
        status = "healthy" if not failed else "failing"
        return {"status": status, "summary": summary["summary"], "failed": failed}

    def diagnose(self, failed):
        settings = run_tool(self, "aws_inspect")
        return self.think(
            f"Failed checks:\n{json.dumps(failed)}\n\nCurrent AWS settings:\n{json.dumps(settings)}\n"
            'Reply with JSON: {"root_cause": "...", "evidence": "...", "proposed_fix": "<fix name or none>", "explanation": "..."}',
            ["root_cause", "evidence", "proposed_fix", "explanation"],
        )
