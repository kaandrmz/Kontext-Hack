"""
Website to Context Analysis Tool

This script crawls websites using Firecrawl API and analyzes them using OpenAI GPT API
to extract structured product insights.

Required environment variables:
- OPENAI_API_KEY: Your OpenAI API key
- FIRECRAWL_API_KEY: Your Firecrawl API key (get from firecrawl.dev)

Install dependencies:
pip install openai requests python-dotenv
"""

import openai
import json
import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Firecrawl API configuration
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"

def analyze_website_content(scraped_website_content: str) -> Dict[str, Any]:
    """
    Sends scraped website content to GPT API for product analysis.
    
    Args:
        scraped_website_content (str): The raw scraped website content
        
    Returns:
        Dict[str, Any]: Parsed JSON response from GPT API
    """
    
    system_prompt = """You are a precise SaaS/product analyst. You will receive a scraped website (raw text, headings, testimonials, images, sometimes messy formatting). Your task is to extract structured, concise insights about the product. Only use information that clearly appears in the scrape, do not hallucinate.

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

def crawl_and_analyze_website(url: str) -> Dict[str, Any]:
    """
    Crawls a website using Firecrawl and then analyzes it with GPT.
    
    Args:
        url (str): The website URL to crawl and analyze
        
    Returns:
        Dict[str, Any]: Analysis results from GPT API
    """
    
    print(f"Step 1: Crawling website: {url}")
    scraped_content = crawl_website(url)
    
    if not scraped_content:
        print("Failed to crawl website")
        return None
    
    print(f"Step 2: Analyzing scraped content ({len(scraped_content)} characters)")
    analysis_result = analyze_website_content(scraped_content)
    
    return analysis_result

def main():
    """
    Main function to crawl and analyze the Cal AI website.
    """
    
    # Cal AI website URL
    cal_ai_url = "https://www.calai.app/"
    
    print("Starting Cal AI website analysis...")
    result = crawl_and_analyze_website(cal_ai_url)
    
    if result:
        print("Analysis complete!")
        print(json.dumps(result, indent=2))
    else:
        print("Analysis failed.")

if __name__ == "__main__":
    main()
