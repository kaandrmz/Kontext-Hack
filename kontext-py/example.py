#!/usr/bin/env python3
"""
Simple example of using the Kontext API client to get personalized context
and use it with an LLM for a chat interaction.
"""

import os
from pathlib import Path
from kontext_client import KontextClientSync, KontextError


def main():
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

    # Get API key from environment variable
    api_key = os.getenv("KONTEXT_API_KEY")
    if not api_key:
        print("Error: Please set KONTEXT_API_KEY in .env file or environment variable")
        print("Example: export KONTEXT_API_KEY='your-api-key-here'")
        return

    # Optional: Set custom API URL if using a local or custom instance
    api_url = os.getenv("KONTEXT_API_URL", "https://api.kontext.dev")
    
    # Debug: Print the values to verify they're correct
    print(f"Debug - API Key: {api_key[:10]}..." if api_key else "None")
    print(f"Debug - API URL: {api_url}")

    # Create the Kontext client
    client = KontextClientSync(api_key, api_url)

    # User ID (in a real app, this would come from your authentication system)
    user_id = "x5gbu7dvpaXkrFxEzQHZIbbSzU19nWfd"

    print(f"Getting personalized context for user: {user_id}\n")

    try:
        # Get personalized context for the user
        context = client.get_context(
            user_id=user_id,
            task="chat",  # Task type: "chat", "general", etc.
            max_tokens=500,  # Limit context size
            use_identity_mode=True,  # Use identity-based personalization
            # privacy_level="none",  # Privacy level: "strict", "moderate", "none"
        )

        # Display the results
        print("=" * 60)
        print("PERSONALIZED SYSTEM PROMPT:")
        print("=" * 60)
        print(context["systemPrompt"])
        print("=" * 60)

        print("\nContext Information:")
        print(f"  - Token count: {context['tokenCount']}")
        print(f"  - User ID: {context['metadata']['userId']}")
        print(f"  - Providers: {', '.join(context['metadata']['providers'])}")

        # Example: Use the context with a chat prompt
        print("\n" + "=" * 60)
        print("EXAMPLE CHAT INTERACTION:")
        print("=" * 60)

        user_message = input("\nEnter a message to send with personalized context: ")

        print("\nIn a real application, you would now send:")
        print("1. System Prompt: [The personalized context above]")
        print(f"2. User Message: {user_message}")
        print("   to your preferred LLM (OpenAI, Anthropic, etc.)")

        # Example of how you might use this with OpenAI
        print("\n" + "=" * 60)
        print("EXAMPLE CODE FOR OPENAI INTEGRATION:")
        print("=" * 60)
        print("""
from openai import OpenAI

openai_client = OpenAI(api_key="your-openai-key")

response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": context["systemPrompt"]},
        {"role": "user", "content": user_message}
    ]
)

print(response.choices[0].message.content)
        """)

    except KontextError as e:
        print(f"\nError getting context: {e}")
        print(f"Error code: {e.code}")
        if e.status_code:
            print(f"HTTP status: {e.status_code}")

        # Handle specific error cases
        if e.code == "UNAUTHORIZED_USER":
            print("\nThe user needs to connect their account first.")
        elif e.code == "INVALID_USER_ID":
            print("\nPlease provide a valid user ID.")
        elif e.code == "API_ERROR":
            print(
                "\nThere was an issue with the API. Please check your API key and try again."
            )


if __name__ == "__main__":
    main()
