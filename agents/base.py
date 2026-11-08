"""base.py - the shared code every agent uses.

An agent = a role (instructions for Gemini) + a list of tools it may use
+ its own conversation history for this run.
"""
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # loads GEMINI_API_KEY and GEMINI_MODEL from .env
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
client = genai.Client(
    http_options=types.HttpOptions(
        timeout=120000,  # give up on one request after 60 seconds
        retry_options=types.HttpRetryOptions(attempts=3),  # retry at most 3 times
    )
)


class Agent:
    name = "agent"
    role = "You are a helpful agent."
    tools = []  # names of the tools this agent is allowed to use

    def __init__(self, log):
        self.log = log
        self.history = []  # this agent's own memory for the current run

    def think(self, message, required_keys):
        """Send a message to Gemini and get back a JSON reply (a dict).

        The reply must contain every key in required_keys. If it doesn't,
        Gemini is asked once more with the problem explained.
        """
        self.history.append(types.Content(role="user", parts=[types.Part(text=message)]))

        for attempt in range(2):
            response = client.models.generate_content(
                model=MODEL,
                contents=self.history,
                config=types.GenerateContentConfig(
                    system_instruction=self.role,
                    response_mime_type="application/json",
                    temperature=0.2,
                    thinking_config=types.ThinkingConfig(thinking_level="low"),
                ),
            )
            text = response.text or ""
            self.history.append(types.Content(role="model", parts=[types.Part(text=text)]))

            try:
                data = json.loads(text)
                missing = [key for key in required_keys if key not in data]
                if not missing:
                    self.log.write(self.name, "LLM decision", data)
                    return data
                problem = f"missing keys {missing}"
            except json.JSONDecodeError as error:
                problem = f"not valid JSON ({error})"

            self.log.write(self.name, "LLM retry", {"attempt": attempt + 1, "problem": problem})
            fix_request = (
                f"Your last reply was invalid: {problem}. "
                f"Reply again with only a JSON object containing these keys: {required_keys}."
            )
            self.history.append(types.Content(role="user", parts=[types.Part(text=fix_request)]))

        raise ValueError(f"{self.name}: Gemini did not return valid JSON after 2 tries")
