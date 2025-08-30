#!/usr/bin/env python3
import os
from pathlib import Path
from kontext_client import KontextClientSync, KontextError

# Try to load from .env file if it exists
env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                if "KONTEXT_API_KEY" in line:
                    # Handle both 'export KEY=value' and 'KEY=value' formats
                    line = line.replace("export ", "")
                    key, value = line.strip().split("=", 1)
                    # Remove quotes if present
                    value = value.strip().strip("'\"")
                    os.environ[key] = value

# Get API key
api_key = os.getenv("KONTEXT_API_KEY")
if not api_key:
    print("Set KONTEXT_API_KEY in .env file or environment variable")
    exit(1)

try:
    # Create client
    client = KontextClientSync(api_key)

    # Get context
    context = client.get_context(user_id="test-user", task="chat")

    # Print the personalized response
    print(context["systemPrompt"])

except KontextError as e:
    print(f"Error: {e}")
    if e.code == "API_ERROR":
        print("\nMake sure your API key is valid and starts with 'ktext_'")
    exit(1)
