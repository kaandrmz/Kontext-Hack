import re
import os
import json
from typing import List, Dict, Any, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def parse_script(script_text):
    """
    Parse podcast script in format:
    {person1}
    Hey, blabla ...
    {person2}
    blablabla...
    
    Returns list of dictionaries with 'speaker' and 'text' keys
    """
    segments = []
    
    # Split by lines and process
    lines = script_text.strip().split('\n')
    current_speaker = None
    current_text = []
    
    for line in lines:
        line = line.strip()
        
        # Check if line is a speaker marker {person1}, {person2}, etc.
        speaker_match = re.match(r'\{([^}]+)\}', line)
        
        if speaker_match:
            # Save previous segment if it exists
            if current_speaker and current_text:
                segments.append({
                    'speaker': current_speaker,
                    'text': ' '.join(current_text).strip()
                })
            
            # Start new segment
            current_speaker = speaker_match.group(1)
            current_text = []
        else:
            # Add text line to current speaker
            if line and current_speaker:
                current_text.append(line)
    
    # Don't forget the last segment
    if current_speaker and current_text:
        segments.append({
            'speaker': current_speaker,
            'text': ' '.join(current_text).strip()
        })
    
    return segments

def parse_script_file(file_path):
    """Parse script from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        script_text = f.read()
    return parse_script(script_text)

def parse_clips_json(clips_data: Dict[str, Any], clip_index: int = 0) -> List[Dict[str, str]]:
    """
    Parse clips JSON output from podcast_editor.py and convert to script segments.
    
    Args:
        clips_data (Dict[str, Any]): JSON output from podcast_editor.py
        clip_index (int): Which clip to use (0 = top-ranked, default: 0)
        
    Returns:
        List[Dict[str, str]]: List of segments with 'speaker' and 'text' keys
    """
    
    if not clips_data or "clips_ranked" not in clips_data:
        raise ValueError("Invalid clips data: missing 'clips_ranked' field")
    
    clips = clips_data["clips_ranked"]
    if not clips or len(clips) <= clip_index:
        raise ValueError(f"No clip found at index {clip_index}")
    
    selected_clip = clips[clip_index]
    dialogue_lines = selected_clip.get("dialogue_lines", [])
    
    if not dialogue_lines:
        raise ValueError("No dialogue lines found in selected clip")
    
    # Convert dialogue lines to script segments
    segments = []
    for line in dialogue_lines:
        speaker = line.get("speaker", "Unknown")
        text = line.get("text", "")
        
        # Map Speaker A/B to person1/person2 for compatibility
        if speaker == "Speaker A":
            speaker = "person1"
        elif speaker == "Speaker B":
            speaker = "person2"
        
        if text.strip():  # Only add non-empty text
            segments.append({
                "speaker": speaker,
                "text": text.strip()
            })
    
    return segments

def parse_clips_from_file(file_path: str, clip_index: int = 0) -> List[Dict[str, str]]:
    """
    Parse clips JSON file and convert to script segments.
    
    Args:
        file_path (str): Path to JSON file containing clips data
        clip_index (int): Which clip to use (0 = top-ranked, default: 0)
        
    Returns:
        List[Dict[str, str]]: List of segments with 'speaker' and 'text' keys
    """
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            clips_data = json.load(f)
        
        return parse_clips_json(clips_data, clip_index)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")

def detect_script_format(file_path: str) -> str:
    """
    Detect whether a file contains traditional script format or clips JSON.
    
    Args:
        file_path (str): Path to the script file
        
    Returns:
        str: 'traditional' or 'clips_json'
    """
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Try to parse as JSON first
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "clips_ranked" in data:
                return "clips_json"
        except json.JSONDecodeError:
            pass
        
        # Check for traditional format markers
        if re.search(r'\{[^}]+\}', content):
            return "traditional"
        
        return "unknown"
        
    except Exception:
        return "unknown"

def parse_script_auto(file_path: str, clip_index: int = 0) -> List[Dict[str, str]]:
    """
    Automatically detect script format and parse accordingly.
    
    Args:
        file_path (str): Path to script file (traditional or clips JSON)
        clip_index (int): Which clip to use if JSON format (default: 0)
        
    Returns:
        List[Dict[str, str]]: List of segments with 'speaker' and 'text' keys
    """
    
    format_type = detect_script_format(file_path)
    
    if format_type == "clips_json":
        print(f"📊 Detected clips JSON format, using clip index {clip_index}")
        return parse_clips_from_file(file_path, clip_index)
    elif format_type == "traditional":
        print("📝 Detected traditional script format")
        return parse_script_file(file_path)
    else:
        raise ValueError(f"Unknown script format in file: {file_path}")

def list_available_clips(file_path: str) -> None:
    """
    Display available clips from a clips JSON file.
    
    Args:
        file_path (str): Path to clips JSON file
    """
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            clips_data = json.load(f)
        
        clips = clips_data.get("clips_ranked", [])
        
        print(f"\n📊 Available clips in {file_path}:")
        print("=" * 60)
        
        for i, clip in enumerate(clips):
            print(f"Clip {i} (Rank {clip.get('rank', 'N/A')}):")
            print(f"  🎯 Relevance: {clip.get('relevance_score_0_1', 0):.2f}")
            print(f"  🚀 Viral Score: {clip.get('viral_rationale', {}).get('score_total_0_10', 0)}")
            print(f"  ⏱️  Duration: {clip.get('start_time', 'N/A')} - {clip.get('end_time', 'N/A')}")
            print(f"  🎪 Hook: {clip.get('hook_text', 'N/A')[:80]}...")
            print(f"  🎯 App Mention: {clip.get('app_mention_present', False)}")
            print("-" * 60)
        
    except Exception as e:
        print(f"❌ Error reading clips file: {e}")

if __name__ == "__main__":
    # Test with traditional script format
    print("🧪 Testing traditional script format:")
    sample_script = """
{person1}
Hey there! Welcome to our podcast today.

{person2}
Thanks for having me! I'm excited to be here.

{person1}
So tell me, what got you started in this field?

{person2}
Well, it all began when I was in college...
"""
    
    segments = parse_script(sample_script)
    for i, segment in enumerate(segments):
        print(f"Segment {i+1}:")
        print(f"Speaker: {segment['speaker']}")
        print(f"Text: {segment['text']}")
        print("-" * 50)
    
    # Test with sample clips JSON format
    print("\n🧪 Testing clips JSON format:")
    sample_clips_data = {
        "topic": "calorie tracking, nutrition",
        "audience": "fitness enthusiasts",
        "clips_ranked": [
            {
                "rank": 1,
                "dialogue_lines": [
                    {"speaker": "Speaker A", "text": "You know what's crazy about tracking food?"},
                    {"speaker": "Speaker B", "text": "Yeah, most people just guess portions."},
                    {"speaker": "Speaker A", "text": "I just snap a photo in Cal AI and it gives me macros."},
                    {"speaker": "Speaker B", "text": "That's actually pretty smart for consistency."}
                ],
                "app_mention_present": True,
                "relevance_score_0_1": 0.95
            }
        ]
    }
    
    try:
        clips_segments = parse_clips_json(sample_clips_data, 0)
        print("✅ Clips JSON parsing successful:")
        for i, segment in enumerate(clips_segments):
            print(f"Segment {i+1}:")
            print(f"Speaker: {segment['speaker']}")
            print(f"Text: {segment['text']}")
            print("-" * 50)
    except Exception as e:
        print(f"❌ Error testing clips JSON: {e}")
