"""orchestrator.py - runs the four agents and passes messages between them.

Usage:
    python3 orchestrator.py --verify-only
    python3 orchestrator.py --goal "Add a December trail run to the events page"
"""
import argparse
import os
import time
import json

from agents.deployer import Deployer
from agents.developer import Developer
from agents.planner import Planner
from agents.runlog import RunLog
from agents.validator import FIXES, Validator
from agents.incident_manager import IncidentManager
from agents.test_engineer import TestEngineer

ROOT = os.path.dirname(os.path.abspath(__file__))


class Orchestrator:
    def __init__(self):
        self.log = RunLog()
        self.planner = Planner(self.log)
        self.developer = Developer(self.log)
        self.deployer = Deployer(self.log)
        self.validator = Validator(self.log)

    def send(self, sender, receiver, kind, content):
        """Every hand-off between agents goes through here and into the log."""
        self.log.write(sender, "message", {"to": receiver, "type": kind, "content": content})

    def approve(self, what, details):
        """Ask the human before any consequential change."""
        print("\n" + "=" * 60)
        print(f"APPROVAL NEEDED: {what}")
        print(details)
        answer = input("Type yes to approve: ").strip().lower()
        approved = answer == "yes"
        self.log.write("human", "approval", {"request": what, "details": details, "approved": approved})
        return approved

    def check_and_repair(self):
        """Verify the site. If it fails: diagnose, ask for approval, fix, verify again."""
        result = self.validator.verify()
        self.send("validator", "orchestrator", "verify_result", result)
        if result["status"] == "healthy":
            return True

        diagnosis = self.validator.diagnose(result["failed"])
        fix = diagnosis["proposed_fix"]
        self.send("validator", "orchestrator", "proposed_fix", diagnosis)
        if fix not in FIXES:
            print("\nNo approved fix fits this problem. A human needs to look at it.")
            return False

        details = f"Root cause: {diagnosis['root_cause']}\nFix: {fix} - {FIXES[fix]}\nWhy: {diagnosis['explanation']}"
        if not self.approve(f"Apply fix '{fix}'", details):
            print("\nFix rejected. Nothing was changed.")
            return False

        self.send("orchestrator", "deployer", "apply_fix", {"fix": fix})
        applied = self.deployer.apply_fix(fix)
        self.send("deployer", "orchestrator", "fix_result", applied)
        if not applied["ok"]:
            return False

        # AWS changes can take a little while to take effect, so re-check a few times.
        for attempt in range(1, 7):
            time.sleep(20)
            result = self.validator.verify()
            self.send("validator", "orchestrator", "recheck_result", {"attempt": attempt, **result})
            if result["status"] == "healthy":
                return True
        return False

    def run_goal(self, goal):
        with open(os.path.join(ROOT, "config", "requirements.md")) as f:
            requirements = f.read()
        self.send("human", "planner", "goal", {"goal": goal})
        plan = self.planner.plan(goal, requirements)
        for task in plan["tasks"]:
            self.send("planner", task["agent"], "task", task)
            if task["agent"] == "developer" and task["action"] == "edit_site":
                result = self.developer.edit_site(task)
            elif task["agent"] == "deployer" and task["action"] == "deploy":
                result = self.deployer.deploy(task, self.approve)
            elif task["agent"] == "validator" and task["action"] == "verify":
                result = {"healthy": self.check_and_repair()}
            else:
                result = {"ok": False, "error": "unknown agent or action"}
            self.send(task["agent"], "orchestrator", "task_result", {"task": task["id"], **result})
            if result.get("ok") is False:
                print(f"\nStopping: task {task['id']} did not succeed.")
                return False
        return True

    def write_tests(self):
        """Test Engineer writes new tests from the requirements and runs them."""
        with open(os.path.join(ROOT, "config", "requirements.md")) as f:
            requirements = f.read()
        self.send("orchestrator", "test_engineer", "task", {"action": "write_tests"})
        result = self.test_engineer.write_tests(requirements)
        self.send("test_engineer", "orchestrator", "task_result", result)
        print("\nSaved", result["saved"], "tests.", result["passed"], "/", result["total"], "tests pass.")
        print("Commit tests/generated/agent_tests.json so the pipeline runs them too.")
        return result["ok"]

    def check_pipeline(self):
        """Deployer checks that the pipeline is set up correctly."""
        self.send("orchestrator", "deployer", "task", {"action": "check_pipeline"})
        result = self.deployer.check_pipeline()
        self.send("deployer", "orchestrator", "task_result", result)
        return result["ok"]

    def diagnose(self):
        """Incident Manager diagnoses the latest failed run, then hands off to the right agent."""
        self.send("orchestrator", "incident_manager", "task", {"action": "diagnose_latest_failure"})
        report = self.incident_manager.diagnose()
        self.send("incident_manager", "orchestrator", "diagnosis", report)
        if not report["ok"]:
            return False

        if report["failed_stage"] == "Build":
            # tests failed before deploy: ask the Test Engineer to confirm it on the same code
            self.send("incident_manager", "test_engineer", "confirm_test_failure",
                      {"commit": report["commit"], "root_cause": report["diagnosis"]["root_cause"]})
            check = self.test_engineer.explain_results()
            self.send("test_engineer", "incident_manager", "confirmation", check)
        else:
            # deploy or verify failed: ask the Validator to confirm the live site is healthy again
            self.send("incident_manager", "validator", "confirm_site_healthy",
                      {"known_good_release": report["known_good_release"]})
            check = self.validator.verify()
            self.send("validator", "incident_manager", "confirmation", check)

        os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
        path = os.path.join(ROOT, "reports", "incident-" + report["commit"][:8] + ".json")
        json.dump({"report": report, "confirmation": check}, open(path, "w"), indent=2)
        print("\n" + "=" * 60)
        print("Failed stage:", report["failed_stage"], "| commit:", report["commit"][:8])
        print("Root cause:", report["diagnosis"]["root_cause"])
        print("Fix:", report["diagnosis"]["recommended_fix"])
        print("Known-good release:", report["known_good_release"])
        print("Saved:", path)
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Fieldline multi-agent system")
    parser.add_argument("--goal", help="what you want the agents to do")
    parser.add_argument("--verify-only", action="store_true", help="only check (and repair) the live site")
    parser.add_argument("--write-tests", action="store_true", help="Test Engineer writes new tests")
    parser.add_argument("--check-pipeline", action="store_true", help="Deployer checks the pipeline setup")
    parser.add_argument("--diagnose", action="store_true", help="Incident Manager diagnoses the last failed run")
    args = parser.parse_args()

    orchestrator = Orchestrator()
    if args.verify_only:
        ok = orchestrator.check_and_repair()
    elif args.goal:
        ok = orchestrator.run_goal(args.goal)
    else:
        parser.error("use --goal \"...\" or --verify-only")
    print("\nRESULT:", "success" if ok else "needs attention")
    print("Log:", orchestrator.log.path)
