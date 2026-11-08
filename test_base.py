"""Quick test: one agent asks Gemini one question and gets JSON back."""
from agents.base import Agent
from agents.runlog import RunLog


class TestAgent(Agent):
    name = "test"
    role = "You are a test agent. Always reply with a JSON object."


log = RunLog()
agent = TestAgent(log)
reply = agent.think("Name one benefit of HTTPS. Use the keys 'benefit' and 'why'.", ["benefit", "why"])
print("\nReply as a Python dict:", reply)
print("Log saved to:", log.path)
