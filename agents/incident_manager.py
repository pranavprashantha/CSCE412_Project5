"""Incident Manager: diagnoses failed pipeline runs and finds the known-good release."""
import json

from .base import Agent
from .tooling import run_tool

ROLE = """You are the Incident Manager agent for a CI/CD pipeline that deploys a static website.
The pipeline stages are: Source (GitHub) -> Build (runs tests) -> Deploy (S3 + CloudFront) -> Verify (checks the live site).
If Build fails, nothing was deployed. If Verify fails, the pipeline already rolled back to the known-good release.

You are given evidence from a failed run: which stage failed and the end of its build log.
Base your diagnosis only on that evidence. Quote the exact log lines that show the problem.

Reply with JSON:
{"observed_failure": "...", "root_cause": "...", "affected_stage": "...",
 "evidence": ["exact log line", "..."], "recommended_fix": "...", "production_impact": "..."}"""


class IncidentManager(Agent):
    name = "incident_manager"
    role = ROLE
    tools = ["pipeline_last_failure", "known_good"]

    def diagnose(self):
        failure = run_tool(self, "pipeline_last_failure")
        if not failure.get("found"):
            return {"ok": False, "error": "no failed run found"}
        releases = run_tool(self, "known_good")

        reply = self.think(
            "Failed run:\n" + json.dumps(failure, indent=2) + "\n\nReleases:\n" + json.dumps(releases, indent=2),
            ["observed_failure", "root_cause", "affected_stage", "evidence", "recommended_fix", "production_impact"],
        )
        # Plain-code rule: the stage, commit and known-good release come from AWS, not from the AI.
        return {
            "ok": True,
            "commit": failure["commit"],
            "failed_stage": failure["failed_stage"],
            "known_good_release": releases["known_good"],
            "rolled_back": failure["failed_stage"] == "Verify",
            "diagnosis": reply,
        }