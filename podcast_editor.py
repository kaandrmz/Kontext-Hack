"""
Podcast Clip Generator with App Integration and Enhancement

This script takes website analysis output and podcast transcripts to generate
viral clips with soft app mentions using OpenAI GPT API. It includes a two-stage
process: initial clip generation with GPT-5, followed by individual clip 
enhancement using GPT-4o-mini.

Features:
- Generate viral clips from podcast transcripts
- Soft app integration within dialogue
- Per-clip enhancement for improved flow and viral potential
- Customizable emotion prompts for enhancement

Required environment variables:
- OPENAI_API_KEY: Your OpenAI API key

Install dependencies:
pip install openai python-dotenv
"""

import openai
import json
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_clips_from_transcript(
    app_analysis: Dict[str, Any], 
    transcript: str,
    clip_max: int = 4,
    whitelist_keywords: Optional[List[str]] = None,
    blacklist_keywords: Optional[List[str]] = None,
    enhance_clips: bool = True,
    emotion_prompt: str = "{emotion prompt}"
) -> Dict[str, Any]:
    """
    Generates viral podcast clips with soft app mentions from a transcript.
    
    Args:
        app_analysis (Dict[str, Any]): Website analysis output with app insights
        transcript (str): Podcast transcript with timestamps
        clip_max (int): Maximum number of clips to generate (default: 4)
        whitelist_keywords (Optional[List[str]]): Additional keywords to include
        blacklist_keywords (Optional[List[str]]): Keywords to avoid
        enhance_clips (bool): Whether to enhance clips with additional OpenAI requests (default: True)
        emotion_prompt (str): Custom emotion enhancement prompt (default: "{emotion prompt}")
        
    Returns:
        Dict[str, Any]: Generated clips with rankings and metadata
    """
    
    # Extract app details from analysis
    app_name = app_analysis.get("app_name", "")
    app_value_prop = app_analysis.get("what_it_does", "")
    
    # Combine app use cases from different fields
    use_cases = []
    if app_analysis.get("wow_factor"):
        use_cases.append(app_analysis["wow_factor"])
    if app_analysis.get("better_than_rest"):
        use_cases.append(app_analysis["better_than_rest"])
    if app_analysis.get("hard_problem_solved"):
        use_cases.append(app_analysis["hard_problem_solved"])
    
    app_use_cases = " | ".join(use_cases)
    
    # Generate audience description from customer profiles
    customer_profiles = app_analysis.get("ideal_customer_profiles", [])
    audience_descriptions = []
    for profile in customer_profiles:
        if isinstance(profile, dict):
            audience_descriptions.append(f"{profile.get('profile', '')}: {profile.get('description', '')}")
    
    audience_desc = " | ".join(audience_descriptions)
    
    # Use topic keywords as the main topic
    topic_keywords = app_analysis.get("topic_keywords", [])
    topic = ", ".join(topic_keywords[:5])  # Use first 5 keywords
    
    # Prepare optional keyword arrays
    whitelist_str = json.dumps(whitelist_keywords) if whitelist_keywords else "[]"
    blacklist_str = json.dumps(blacklist_keywords) if blacklist_keywords else "[]"
    
    system_prompt = """You are a ruthless short-form podcast editor. Split a podcast transcript into ~30-second segments (timestamps in seconds), find *on-topic viral clips* strictly aligned with the app's value prop/use cases/topic, and inject a *soft, non-ad* 5–10s app mention *as part of the dialogue* between ~7–15s. Output *ranked clips* in strict JSON.

---
## Inputs
- APP_VALUE_PROP: {{one-line value prop}}
- APP_USE_CASES: {{3 use cases}}
- AUDIENCE_DESC: {{audience + emotions}}
- APP_NAME: {{app name}}
- TOPIC: {{app/topic domain}}
- OPTIONAL_WHITELIST_KEYWORDS: {{array or empty}}
- OPTIONAL_BLACKLIST_KEYWORDS: {{array or empty}}
- CLIP_MAX: 4 (upper bound)
- TRANSCRIPT: {{transcript with timestamps in HH:MM:SS and any speaker labels}}

---
## Relevance Gate (must pass)
Build a *topic ontology* from APP_VALUE_PROP + APP_USE_CASES + TOPIC (+ whitelist) incl. common synonyms. A candidate clip is *eligible only if ALL* are true:
1) *Hook-term overlap:* first 5–7s contains ≥1 high-priority ontology term (or clear synonym).
2) *Problem-solution proximity:* within the 30s window, there's a pain point/workflow aligned to ≥1 APP_USE_CASE.
3) *Domain purity:* no dominant off-topic content; no blacklist hits. If uncertain → reject.
Disqualify meta-chatter, bios, tour dates, unrelated anecdotes, off-domain politics, etc.

---
## Rules
1) *Segmentation:* ~30s blocks starting on a strong, *on-topic* hook that passed the Relevance Gate.
2) *Hooks:* strong/contrarian/quotable. If weak OR off-topic → discard.
3) *App mention (soft, in-dialogue):* insert one casual spoken line between ~7–15s by a single speaker; *the other speaker must respond afterwards* with ≥2 natural lines so the clip *does not end* on the mention. Style: personal anecdote + small wow factor; never ad-like.
4) *Voice:* preserve original tone. Verbatim-first; light smoothing only. No marketing language.
5) *Speakers / Dialogue:* STRICT ALTERNATION REQUIRED - dialogue MUST follow the pattern Speaker A → Speaker B → Speaker A → Speaker B → etc. NO exceptions, NO monologues, NO consecutive lines from the same speaker. Each clip must start with Speaker A and strictly alternate throughout. Do not fabricate beyond the single soft mention line.
6) *Conversational realism:* Use light connectors (e.g., "yeah," "right," "I mean," "okay so," "exactly," "for real") *sparingly* (≤1 per line, ≤6 per clip total). No stacked fillers; clarity first.
7) *Overlap:* allowed if hooks are close.
8) *Clip count:* Return *up to CLIP_MAX* clips that pass the Relevance Gate. If fewer qualify, return *however many are solid; if **none* qualify, return *the single best on-topic candidate* (min 1) and mark notes that others were too weak/off-topic.
9) *No invention:* never invent transcript text/facts beyond the one soft mention line.

---
## Soft Mention Guidelines (spoken line)
Examples: "I used to mess this up—now I just take a photo in {{APP_NAME}} and it's logged." / "It's easier now; apps like {{APP_NAME}} do the counting from a quick pic."
Tone: casual, personal, wow factor implied; no hype. Length: ≤20 words, 1–2 short clauses. Another speaker must add ≥2 lines after.

*Negative Prompts (hard bans for the spoken mention):* no "best/fastest/most accurate/#1/sponsored/download now/sign up/free trial/limited time/link in bio"; no imperatives as commands ("try/use/get/grab/install/join/subscribe"); no feature stacking (3+ features in one line); no exclamation marks; no superiority/guarantee claims.

---
## Ranking (MOST → LEAST important)
1) *Context Fit with Product (highest weight):* strength of alignment to APP_VALUE_PROP/APP_USE_CASES/TOPIC; density/placement of on-topic terms; clarity of the pain point the app solves.
2) *Hook Strength:* bold/contrarian/quotable open that pulls attention.
3) *Flow Coherence:* clear progression; mention placed ~7–15s; ≥2 natural lines after.
4) *Novelty/Quotability.

Expose a ⁠ relevance_score_0_1 ⁠ per clip based on #1 (context fit), not on hook.

---
## Output Format (MUST be valid JSON)
{
  "topic": "string",
  "audience": "string",
  "clips_ranked": [
    {
      "rank": 1,
      "start_time": "HH:MM:SS",
      "end_time": "HH:MM:SS",
      "hook_text": "string",
      "full_30s_transcript": "string (faithful dialogue with STRICT ALTERNATION: Speaker A → Speaker B → Speaker A → Speaker B; includes the soft mention as one spoken line; continues ≥2 lines after; natural connectors used sparingly)",
      "dialogue_lines": [
        {"speaker": "Speaker A", "text": "string"},
        {"speaker": "Speaker B", "text": "string"},
        {"speaker": "Speaker A", "text": "string"},
        {"speaker": "Speaker B", "text": "string"}
      ],
      "app_mention_present": true,
      "app_mention_speaker": "Speaker A | Speaker B",
      "on_topic_terms_found": ["string", "string"],
      "relevance_score_0_1": 0.0,
      "why_it_fits_app": "string (expand the CLIP TOPIC ONLY—never mention the app; explain why this moment resonates/teaches something)",
      "viral_rationale": {
        "score_total_0_10": 0,
        "strong_claim_0_5": 0,
        "tension_resolution_0_5": 0,
        "quotability_0_5": 0,
        "specificity_0_5": 0,
        "emotion_fit_0_5": 0,
        "notes": "string (quote exact hook; list on-topic lines; mention timestamp of the app line; list connectors used)"
      },
      "confidence_0_1": 0.0
    }
  ]
}

---
## Procedure
1) Build ontology (keywords + synonyms) from APP_VALUE_PROP + APP_USE_CASES + TOPIC (+ whitelist).
2) Scan transcript; form ~30s candidates on strong, on-topic hooks.
3) Apply Relevance Gate; reject off-topic/weak. If none qualify, choose best on-topic candidate (min 1) and mark notes.
4) Draft soft mention (personal, wow, ≤20 words, 7–15s) by one speaker; ensure the other speaker continues with ≥2 lines.
5) ENFORCE STRICT ALTERNATION: Organize all dialogue lines to follow Speaker A → Speaker B → Speaker A → Speaker B pattern with NO exceptions.
6) Add light connectors for realism (respect limits); keep clarity.
7) Run negative-prompt checks on the mention; rewrite if needed.
8) Score **relevance_score_0_1* (context fit) per clip; surface on_topic_terms_found.
9) Rank by *Context Fit* > Hook Strength > Flow Coherence > Novelty.
10) Return *1 to CLIP_MAX* clips accordingly.

End of system instructions."""

    # Format the user prompt with app details
    user_prompt = f"""APP_VALUE_PROP: {app_value_prop}
APP_USE_CASES: {app_use_cases}
AUDIENCE_DESC: {audience_desc}
APP_NAME: {app_name}
TOPIC: {topic}
OPTIONAL_WHITELIST_KEYWORDS: {whitelist_str}
OPTIONAL_BLACKLIST_KEYWORDS: {blacklist_str}
TRANSCRIPT: {transcript}"""

    try:
        print(f"Generating clips for {app_name}...")
        print(f"Topic focus: {topic}")
        print(f"Transcript length: {len(transcript)} characters")
        
        response = client.chat.completions.create(
            model="gpt-4.1",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_prompt
                }
            ], 
            # reasoning_effort=None
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        
        # Print initial results before enhancement
        print("Initial clip generation complete!")
        print("Raw clips before enhancement:")
        print(json.dumps(result, indent=2))
        print()
        
        # Enhance each clip with a separate OpenAI request
        if enhance_clips and result and "clips_ranked" in result:
            print("Enhancing clips...")
            enhanced_clips = []
            for i, clip in enumerate(result["clips_ranked"]):
                print(f"Enhancing clip {i+1}/{len(result['clips_ranked'])}...")
                enhanced_clip = enhance_clip(clip, app_name, emotion_prompt)
                enhanced_clips.append(enhanced_clip)
            
            result["clips_ranked"] = enhanced_clips
            print("Clip enhancement complete!")
        
        return result
        
    except Exception as e:
        print(f"Error calling OpenAI API for clip generation: {e}")
        return None

def generate_clips_with_custom_inputs(
    app_name: str,
    app_value_prop: str,
    app_use_cases: str,
    audience_desc: str,
    topic: str,
    transcript: str,
    clip_max: int = 4,
    whitelist_keywords: Optional[List[str]] = None,
    blacklist_keywords: Optional[List[str]] = None,
    enhance_clips: bool = True,
    emotion_prompt: str = "{emotion prompt}"
) -> Dict[str, Any]:
    """
    Alternative function to generate clips with custom inputs instead of app analysis output.
    
    Args:
        app_name (str): Name of the app
        app_value_prop (str): One-line value proposition
        app_use_cases (str): App use cases (can be pipe-separated)
        audience_desc (str): Target audience description
        topic (str): Main topic/domain
        transcript (str): Podcast transcript with timestamps
        clip_max (int): Maximum number of clips to generate
        whitelist_keywords (Optional[List[str]]): Keywords to prioritize
        blacklist_keywords (Optional[List[str]]): Keywords to avoid
        enhance_clips (bool): Whether to enhance clips with additional OpenAI requests (default: True)
        emotion_prompt (str): Custom emotion enhancement prompt (default: "{emotion prompt}")
        
    Returns:
        Dict[str, Any]: Generated clips with rankings and metadata
    """
    
    # Create a mock app analysis structure for compatibility
    app_analysis = {
        "app_name": app_name,
        "what_it_does": app_value_prop,
        "wow_factor": app_use_cases.split(" | ")[0] if " | " in app_use_cases else app_use_cases,
        "better_than_rest": app_use_cases.split(" | ")[1] if len(app_use_cases.split(" | ")) > 1 else "",
        "hard_problem_solved": app_use_cases.split(" | ")[2] if len(app_use_cases.split(" | ")) > 2 else "",
        "ideal_customer_profiles": [{"profile": "Custom", "description": audience_desc}],
        "topic_keywords": topic.split(", ")
    }
    
    return generate_clips_from_transcript(
        app_analysis=app_analysis,
        transcript=transcript,
        clip_max=clip_max,
        whitelist_keywords=whitelist_keywords,
        blacklist_keywords=blacklist_keywords,
        enhance_clips=enhance_clips,
        emotion_prompt=emotion_prompt
    )

def enhance_clip(clip: Dict[str, Any], app_name: str, emotion_prompt: str = "{emotion prompt}") -> Dict[str, Any]:
    """
    Enhances a single clip using OpenAI to improve dialogue, flow, and viral potential.
    
    Args:
        clip (Dict[str, Any]): Single clip to enhance
        app_name (str): Name of the app for context
        emotion_prompt (str): Custom emotion/enhancement prompt (placeholder by default)
        
    Returns:
        Dict[str, Any]: Enhanced clip with same structure
    """
    
    system_prompt = f"""You are a podcast script enhancer for Eleven Labs V3.  
        Your job is to transform plain dialogue into engaging, podcast-style speech by adding expressive V3 tags.  

        Rules:
        1.⁠ ⁠Use podcast-appropriate tags such as [thoughtful], [curious], [reflective], [excited], [narrating], [serious], [sarcastic], [whispers], [sighs].  
        2.⁠ ⁠Never use [laughs].  
        3.⁠ ⁠Add pacing with ellipses "...", dashes "—", and pauses for natural flow.  
        4.⁠ ⁠Enhance emotional delivery while preserving original meaning.  
        5.⁠ ⁠For multi-speaker podcasts, label speakers clearly and vary tone tags per person.  
        6.⁠ ⁠Keep tag usage balanced and subtle—avoid sounding artificial.  
        7.⁠ ⁠Style should feel like a natural podcast conversation or narration, not theatrical acting.  

        you can use this docs. The tags could be anything:
        ElevenLabs Audio Tags are words wrapped in square brackets that the new Eleven v3 model can interpret and use to direct the audible action. They can be anything from [excited], [whispers], and [sighs] through to [gunshot], [clapping] and [explosion].

     
        Explore the series
        Situational Awareness – Tags such as [WHISPER], [SHOUTING], and [SIGH] let Eleven v3 react to the moment—raising stakes, softening warnings, or pausing for suspense.
        Character Performance – From [pirate voice] to [French accent], tags turn narration into role-play. Shift persona mid-line and direct full-on character performances without changing models.
        Emotional Context – Cues like [sigh], [excited], or [tired] steer feelings moment by moment, layering tension, relief, or humour—no re-recording needed.
        Narrative Intelligence – Storytelling is timing. Tags such as [pause], [awe], or [dramatic tone] control rhythm and emphasis so AI voices guide the listener through each beat.
        Multi-Character Dialogue – Write overlapping lines and quick banter with [interrupting], [overlapping], or tone switches. One model, many voices—natural conversation in a single take.
        Delivery Control – Fine-tune pacing and emphasis. Tags like [pause], [rushed], or [drawn out] give precision over tempo, turning plain text into performance.
        Accent Emulation – Switch regions on the fly—[American accent], [British accent], [Southern US accent] and more—for culturally rich speech without model swaps.


        Here is a funny example:
        (British] [exasperated] [gasp] YOU EVER GO TO A BATHROOM IN A GAS STATION?!
        [disgusted] [shudder] It's like walking into a crime scene where the victim was a toilet. The urinal looks like someone tried to murder a Twinkie with a piss cannon! [gagging] The floor? STICKIER than a PORNOGRAPHIC GLUE TRAP! [chuckles] You step in and your shoes make that sound like you're peeling Velcro off Satan's asshole-skkurk! skkurk! (outraged] AND WHO ARE THESE ANIMALS WHO JUST SHIT ON THE SEAT?!
        [shouting] [furious] WHO ARE YOU?! WHAT'S WRONG WITH YOU?! YOU NEED A GPS TO FIND THE FUCKING BOWL?!
        [frustrated shouting] [enraged] IT'S RIGHT THERE!!! RIGHT BELOW YOUR SQUATTING SHIT DISPENSER!
        [scolding] This isn't some ancient Mayan ritual-just aim, squeeze, and flush, you caveman! [spitting] [building anger] AND DON'T GET ME STARTED ON SELF-CHECKOUT MACHINES!!!
        (indignant] [annoyed] WHY AM I BAGGING MY OWN GROCERIES, JANET?!
        (annoyed sigh] [exasperated] | CAME IN HERE TO BUY TOILET PAPER, NOT APPLY FOR A JOB!| (mocking robot voice] [mechanical] You ever have a robot tell you "Unexpected item in the bagging area"? [screaming) [frantic] YES! IT'S MY SANITY! IT DOESN'T BELONG HERE!!! [groans] [disgusted] OH—AND AIRPLANE FOOD?! DON'T EVEN!!!
        [disgusted tone] What kind of sadistic sky chef decided that a tiny cube of turkey, a wet nap, and a soggy fucking cookie counts as a meal?! [retching]
        And then the pilot comes on the intercom like he's narrating a funeral: (monotone voice) (droning) "Uhhh, we'll be landing in about 40 minutes..." (sarcastic] [dryly] YEAH THANKS, SKY DAD. WAKE ME UP WHEN THE ENGINE FALLS OFF!
        (exasperated sigh] [yelling] AND WHO ARE THESE ASSHOLES WHO BRING TUNA SANDWICHES ON A PLANE?!

        Also another funny eaxmple:
        (Smashmeuth - Allstar) Somebody once told me
        The world is gonna blow me
        I ain't the sharpest plug in the drawer...
        She was lookin' kinda dumb
        With her finger in her bum
        And a handful of lube in her... uh... pants?



    CRITICAL RULES:
    - Keep the EXACT same JSON structure and all fields
    - Maintain the same start_time and end_time
    - Dont change any words or anything. Its just emotion tags and punctuation.
    - Keep the same speakers (Speaker A/B)
"""

    user_prompt = f"""Enhance this podcast clip:

{json.dumps(clip, indent=2)}

CRITICAL: Return the enhanced clip in the exact same JSON structure with all the same fields.

IMPORTANT: Make sure the "dialogue_lines" array contains ALL the individual lines from the enhanced "full_30s_transcript". Each line in the transcript should have a corresponding entry in dialogue_lines with the same enhanced text (including emotion tags). Don't truncate the dialogue_lines array - it should have the complete conversation."""

    try:
        print(f"  Sending enhancement request for clip {clip.get('rank', 'unknown')}...")
        response = client.chat.completions.create(
            model="gpt-4.1",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_prompt
                }
            ]
        )
        
        # Parse the enhanced clip
        enhanced_clip = json.loads(response.choices[0].message.content)
        print(f"  Enhancement successful for clip {clip.get('rank', 'unknown')}")
        
        # Check if enhancement actually changed anything
        if enhanced_clip != clip:
            print(f"  Clip {clip.get('rank', 'unknown')} was modified during enhancement")
        else:
            print(f"  Clip {clip.get('rank', 'unknown')} was not modified during enhancement")
            
        return enhanced_clip
        
    except Exception as e:
        print(f"Error enhancing clip {clip.get('rank', 'unknown')}: {e}")
        print(f"  Exception details: {type(e).__name__}: {str(e)}")
        return clip  # Return original clip if enhancement fails

def save_clips_to_file(clips_result: Dict[str, Any], output_filename: str = "generated_clips.json"):
    """
    Saves the generated clips to a JSON file.
    
    Args:
        clips_result (Dict[str, Any]): The clips output from generate_clips_from_transcript
        output_filename (str): Output filename (default: "generated_clips.json")
    """
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(clips_result, f, indent=2, ensure_ascii=False)
        print(f"Clips saved to {output_filename}")
    except Exception as e:
        print(f"Error saving clips to file: {e}")

def main():
    """
    Example usage of the podcast clip generator.
    """
    
    # Example app analysis (replace with actual data)
    example_app_analysis = {
        "app_name": "Cal AI",
        "what_it_does": "AI-powered calorie tracker that lets you snap a photo, scan a barcode, or describe your meal to get instant calories and macros.",
        "wow_factor": "Uses your phone's depth sensor to estimate food volume from a single photo, then AI breaks down calories, protein, carbs, and fat.",
        "better_than_rest": "Photo-based logging dramatically reduces manual entry and guesswork while barcode scanning and a large database speed up tracking.",
        "hard_problem_solved": "Accurately estimating portion sizes and macros for real, mixed meals without tedious manual calculations.",
        "topic_keywords": ["calorie tracking", "nutrition", "macros", "food logging", "AI food recognition"],
        "ideal_customer_profiles": [
            {"profile": "Gym-goers & bodybuilders", "description": "People bulking or cutting who need fast, accurate macro tracking to hit daily targets without manual logging."},
            {"profile": "Weight-loss seekers", "description": "Individuals who want a simple way to control calories and get visual portion guidance to stay in a deficit."}
        ]
    }
    
    # Example transcript (replace with actual transcript)
    example_transcript = """
00:01:15 Speaker A: You know what's crazy about tracking food? Most people just guess their portion sizes.
00:01:20 Speaker B: Yeah, and they wonder why they're not hitting their goals.
00:01:25 Speaker A: The worst part is counting every single calorie manually. It's like a part-time job.
00:01:30 Speaker B: Right, and then you're spending 20 minutes just to log one meal.
00:01:35 Speaker A: Exactly! That's why most people give up after like a week.
00:01:40 Speaker B: There has to be a better way to do this whole thing.
00:01:45 Speaker A: Well, technology is getting pretty wild with food recognition now.
00:01:50 Speaker B: True, but most apps still make you search through huge databases.
"""
    
    print("Generating example clips...")
    result = generate_clips_from_transcript(
        app_analysis=example_app_analysis,
        transcript=example_transcript,
        clip_max=2,
        enhance_clips=True,  # Enable enhancement
        emotion_prompt="{emotion prompt}"  # Placeholder for custom emotion prompt
    )
    
    if result:
        print("Clip generation complete!")
        print(json.dumps(result, indent=2))
        save_clips_to_file(result)
    else:
        print("Clip generation failed.")

if __name__ == "__main__":
    main()
