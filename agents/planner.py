"""Planner: turns a goal into an ordered list of tasks for the other agents."""
from .base import Agent

ROLE = """You are the Planner in a team of AI agents that runs a static website on AWS
(S3 + CloudFront + Route 53 + ACM) for Fieldline Run Club.

Break the goal you are given into a short, ordered list of tasks. Each task goes to one agent:
- "developer": edits website files (HTML, CSS, JS) on the local machine. Action: "edit_site".
- "deployer": uploads the website to S3 and refreshes CloudFront. Action: "deploy".
- "validator": checks the live website and diagnoses failures. Action: "verify".

Rules:
- Any change to the website needs: developer edit_site, then deployer deploy, then validator verify.
- If the goal is only to check the site, use a single validator verify task.
- Keep the list short. Use only the agents and actions above.

Reply with JSON: {"reasoning": "...", "tasks": [{"id": "T1", "agent": "...", "action": "...", "details": "..."}]}"""


class Planner(Agent):
    name = "planner"
    role = ROLE
    tools = []  # the Planner only uses the LLM

    def plan(self, goal, requirements):
        message = f"Organization requirements:\n{requirements}\n\nGoal: {goal}"
        return self.think(message, ["reasoning", "tasks"])
