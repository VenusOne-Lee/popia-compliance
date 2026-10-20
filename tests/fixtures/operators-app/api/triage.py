# Synthetic fixture for the operator inventory. Not real data.
import sentry_sdk
from anthropic import Anthropic

client = Anthropic()


def triage(patient):
    prompt = f"Summarise: {patient['diagnosis']} for {patient['first_name']}"
    return client.messages.create(model="claude-x", max_tokens=100,
                                  messages=[{"role": "user", "content": prompt}])
