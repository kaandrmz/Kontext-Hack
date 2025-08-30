"""
Website to Context Analysis Tool

This script crawls websites using Firecrawl API and analyzes them using OpenAI GPT API
to extract structured product insights with personalized context from Kontext.

Required environment variables:
- OPENAI_API_KEY: Your OpenAI API key
- FIRECRAWL_API_KEY: Your Firecrawl API key (get from firecrawl.dev)
- KONTEXT_API_KEY: Your Kontext API key (optional, for personalized analysis)
- KONTEXT_API_URL: Kontext API URL (optional, defaults to https://api.kontext.dev)

Install dependencies:
pip install openai requests python-dotenv aiohttp

Note: The kontext_client is included locally in the kontext-py directory.
"""

import openai
import json
import os
import requests
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Add the kontext-py directory to the Python path
kontext_py_path = Path(__file__).parent / "kontext-py"
if kontext_py_path.exists():
    sys.path.insert(0, str(kontext_py_path))

from kontext_client import KontextClientSync, KontextError

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Firecrawl API configuration
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"

# Kontext API configuration
KONTEXT_API_KEY = os.getenv("KONTEXT_API_KEY")
KONTEXT_API_URL = os.getenv("KONTEXT_API_URL", "https://api.kontext.dev")

# Initialize Kontext client if API key is available
kontext_client = None
if KONTEXT_API_KEY:
    kontext_client = KontextClientSync(KONTEXT_API_KEY, KONTEXT_API_URL)

def get_kontext_context(user_id: str = "x5gbu7dvpaXkrFxEzQHZIbbSzU19nWfd") -> str:
    """
    Gets personalized context from Kontext API.
    
    Args:
        user_id (str): The user ID to get context for
        
    Returns:
        str: Personalized context or empty string if unavailable
    """
    if not kontext_client:
        print("Warning: Kontext API key not found, proceeding without personalized context")
        return ""
    
    try:
        context = kontext_client.get_context(
            user_id=user_id,
            task="general",  # Task type for general analysis
            max_tokens=300,  # Limit context size to keep prompt manageable
            use_identity_mode=True,  # Use identity-based personalization
        )
        return context.get("systemPrompt", "")
    except KontextError as e:
        print(f"Warning: Failed to get Kontext context: {e}")
        return ""
    except Exception as e:
        print(f"Warning: Unexpected error getting Kontext context: {e}")
        return ""

def analyze_website_content(scraped_website_content: str, user_id: str = "x5gbu7dvpaXkrFxEzQHZIbbSzU19nWfd") -> Dict[str, Any]:
    """
    Sends scraped website content to GPT API for product analysis with personalized context.
    
    Args:
        scraped_website_content (str): The raw scraped website content
        user_id (str): User ID for personalized Kontext context
        
    Returns:
        Dict[str, Any]: Parsed JSON response from GPT API
    """
    
    # Get personalized context from Kontext
    kontext_context = get_kontext_context(user_id)
    
    # Build the system prompt with optional Kontext context
    base_system_prompt = """You are a precise SaaS/product analyst. You will receive a scraped website (raw text, headings, testimonials, images, sometimes messy formatting). Your task is to extract structured, concise insights about the product. Only use information that clearly appears in the scrape, do not hallucinate."""
    
    # Add Kontext context if available
    if kontext_context:
        system_prompt = f"""{base_system_prompt}

## Additional Context:
Here is extra content about the user's preferences and context: {kontext_context}

Use this additional context to better tailor your analysis and recommendations, but still focus primarily on the scraped website content."""
    else:
        system_prompt = base_system_prompt
    
    # Add the main instructions
    system_prompt += """

## Steps:
1. Identify the *product/app name* (short, exact string).
2. Describe clearly *what it does, its **wow factor, **why it is better than alternatives, and **how it solves a hard problem. Keep this practical and benefit-focused.
3. Extract the **topic / domain keywords: 5–10 keywords describing the product's niche (e.g., nutrition, calorie tracking, fitness, weight loss, health apps).
4. Define **1–4 ideal customer profiles: short descriptions of customer types who would realistically use or buy this product, including their goals and context.
5. Suggest **podcast search keywords*: 5–10 query phrases we could use to find the most relevant podcasts for this product niche.

## Output Format (MUST be valid JSON):
{
  "app_name": "string",
  "what_it_does": "string (1–2 sentences)",
  "wow_factor": "string (what makes it special, 1–2 sentences)",
  "better_than_rest": "string (1–2 sentences)",
  "hard_problem_solved": "string (1–2 sentences)",
  "topic_keywords": ["keyword1", "keyword2", "keyword3"],
  "ideal_customer_profiles": [
    {"profile": "string (short title)", "description": "string (who they are, why they care)"}
  ],
  "podcast_search_keywords": ["string", "string", "string"]
}

If some info is not explicitly given, infer from context logically (e.g., if testimonials mention gym bros, you can list them as a profile). Keep all text concise and factual."""

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": f"SCRAPED_WEBSITE: {scraped_website_content}"
                }
            ]
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def crawl_website(url: str) -> str:
    """
    Crawls a website using Firecrawl API.
    
    Args:
        url (str): The website URL to crawl
        
    Returns:
        str: The scraped content from the website
    """
    
    if not FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY environment variable not set")
    
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Scrape data payload
    scrape_data = {
        "url": url,
        "formats": ["markdown"]
    }
    
    try:
        print(f"Crawling website: {url}")
        
        # Make API call to Firecrawl
        response = requests.post(
            f"{FIRECRAWL_BASE_URL}/scrape",
            headers=headers,
            json=scrape_data
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success") and "data" in result:
            content = result["data"].get("markdown", "")
            if content:
                print(f"Successfully crawled {len(content)} characters")
                return content
            else:
                print("No markdown content found in scrape result")
                return None
        else:
            print(f"Scrape failed: {result.get('error', 'Unknown error')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error calling Firecrawl API: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during crawling: {e}")
        return None

def crawl_and_analyze_website(url: str, user_id: str = "x5gbu7dvpaXkrFxEzQHZIbbSzU19nWfd") -> Dict[str, Any]:
    """
    Crawls a website using Firecrawl and then analyzes it with GPT using personalized context.
    
    Args:
        url (str): The website URL to crawl and analyze
        user_id (str): User ID for personalized Kontext context
        
    Returns:
        Dict[str, Any]: Analysis results from GPT API
    """
    
    print(f"Step 1: Crawling website: {url}")
    scraped_content = crawl_website(url)
    
    if not scraped_content:
        print("Failed to crawl website")
        return None
    
    print(f"Step 2: Analyzing scraped content ({len(scraped_content)} characters)")
    print(f"Step 3: Getting personalized context for user: {user_id}")
    analysis_result = analyze_website_content(scraped_content, user_id)
    
    return analysis_result

def main():
    """
    Main function to crawl and analyze the Cal AI website with personalized context.
    """
    
    # Cal AI website URL
    cal_ai_url = "https://www.calai.app/"
    
    # User ID for personalized context (in production, this would come from your auth system)
    user_id = "x5gbu7dvpaXkrFxEzQHZIbbSzU19nWfd"
    
    print("Starting Cal AI website analysis with personalized context...")
    print(f"Using user ID: {user_id}")
    
    result = crawl_and_analyze_website(cal_ai_url, user_id)
    
    if result:
        print("Analysis complete!")
        print(json.dumps(result, indent=2))
    else:
        print("Analysis failed.")

if __name__ == "__main__":
    main()
