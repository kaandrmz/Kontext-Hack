import os
import asyncio
from typing import Optional, Dict, Any
import aiohttp
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class KontextError(Exception):
    def __init__(self, message: str, code: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class KontextClient:
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.kontext.dev",
        providers: list = None,
    ):
        if not api_key:
            raise KontextError("Kontext API key is required", "MISSING_API_KEY", 400)

        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.providers = providers or ["gmail", "preferences"]

    async def get_context(
        self,
        user_id: str,
        task: str = "general",
        max_tokens: Optional[int] = None,
        use_identity_mode: bool = True,
    ) -> Dict[str, Any]:
        if not user_id or not isinstance(user_id, str):
            raise KontextError(
                "Valid userId is required. Please provide a non-empty string userId.",
                "INVALID_USER_ID",
                400,
            )

        if max_tokens is not None and (
            not isinstance(max_tokens, int) or max_tokens <= 0
        ):
            raise KontextError(
                "maxTokens must be a positive number if provided.",
                "INVALID_MAX_TOKENS",
                400,
            )

        # Prepare the tRPC-style request
        endpoint = f"{self.api_url}/trpc/data.context"

        # tRPC batch format for queries
        params = {
            "batch": 1,
            "input": json.dumps(
                {
                    "0": {
                        "json": {
                            "userId": user_id,
                            "task": task,
                            "maxFacts": min(max_tokens // 10, 100)
                            if max_tokens
                            else None,
                            "cachePolicy": "fresh",
                            "includeRecentData": True,
                        }
                    }
                }
            ),
        }

        # Check if API key starts with 'ktext' to determine header format
        if self.api_key.startswith("ktext"):
            headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        else:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

        async with aiohttp.ClientSession() as session:
            try:
                logger.debug(f"Request URL: {endpoint}")
                logger.debug(f"Request params: {params}")
                logger.debug(f"Request headers: {headers}")
                
                async with session.get(
                    endpoint, params=params, headers=headers
                ) as response:
                    logger.debug(f"Response status: {response.status}")
                    logger.debug(f"Response headers: {dict(response.headers)}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API error response: {error_text}")
                        raise KontextError(
                            f"API request failed: {error_text}",
                            "API_ERROR",
                            response.status,
                        )

                    data = await response.json()

                    # tRPC batch response format
                    if isinstance(data, list) and len(data) > 0:
                        result = (
                            data[0].get("result", {}).get("data", {}).get("json", {})
                        )
                    else:
                        result = data

                    # Transform response to match expected format
                    return {
                        "systemPrompt": result.get(
                            "systemPrompt", "You are a helpful assistant."
                        ),
                        "metadata": {
                            "userId": user_id,
                            "timestamp": result.get("metadata", {}).get(
                                "generatedAt", None
                            ),
                            "providers": ["gmail"],
                        },
                        "tokenCount": len(result.get("systemPrompt", "")) // 4,
                    }

            except aiohttp.ClientError as e:
                raise KontextError(f"Network error: {str(e)}", "NETWORK_ERROR", 500)
            except json.JSONDecodeError as e:
                raise KontextError(
                    f"Invalid JSON response: {str(e)}", "INVALID_RESPONSE", 500
                )

    async def disconnect(self, user_id: str) -> None:
        if not user_id or not isinstance(user_id, str):
            raise KontextError(
                "Valid userId is required for disconnect.", "INVALID_USER_ID", 400
            )

        endpoint = f"{self.api_url}/trpc/gdpr.deleteData"

        # Check if API key starts with 'ktext' to determine header format
        if self.api_key.startswith("ktext"):
            headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        else:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

        # tRPC mutation format
        data = {"json": {"userId": user_id}}

        async with aiohttp.ClientSession() as session:
            try:
                logger.debug(f"Disconnect URL: {endpoint}")
                logger.debug(f"Disconnect data: {data}")
                logger.debug(f"Disconnect headers: {headers}")
                
                async with session.post(
                    endpoint, json=data, headers=headers
                ) as response:
                    logger.debug(f"Disconnect response status: {response.status}")
                    logger.debug(f"Disconnect response headers: {dict(response.headers)}")
                    
                    if response.status not in [200, 204]:
                        error_text = await response.text()
                        logger.error(f"Disconnect error response: {error_text}")
                        if "not found" in error_text.lower():
                            raise KontextError(
                                "User not found. The user may have already been disconnected.",
                                "USER_NOT_FOUND",
                                404,
                            )
                        raise KontextError(
                            f"Disconnect failed: {error_text}",
                            "DISCONNECT_FAILED",
                            response.status,
                        )

            except aiohttp.ClientError as e:
                raise KontextError(
                    f"Network error during disconnect: {str(e)}", "NETWORK_ERROR", 500
                )


# Synchronous wrapper for easier usage
class KontextClientSync:
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.kontext.dev",
        providers: list = None,
    ):
        self.client = KontextClient(api_key, api_url, providers)

    def get_context(
        self,
        user_id: str,
        task: str = "general",
        max_tokens: Optional[int] = None,
        use_identity_mode: bool = True,
    ) -> Dict[str, Any]:
        return asyncio.run(
            self.client.get_context(user_id, task, max_tokens, use_identity_mode)
        )

    def disconnect(self, user_id: str) -> None:
        return asyncio.run(self.client.disconnect(user_id))


# Example usage
if __name__ == "__main__":
    # Get API key from environment variable
    api_key = os.getenv("KONTEXT_API_KEY")
    if not api_key:
        print("Please set KONTEXT_API_KEY environment variable")
        exit(1)

    # Create synchronous client
    client = KontextClientSync(api_key)

    try:
        # Get context for a user
        context = client.get_context(
            user_id="test-user-123", task="chat", max_tokens=500
        )

        print("System Prompt:")
        print(context["systemPrompt"])
        print(f"\nToken Count: {context['tokenCount']}")
        print(f"Metadata: {context['metadata']}")

    except KontextError as e:
        print(f"Error: {e}")
        print(f"Code: {e.code}")
        print(f"Status: {e.status_code}")
