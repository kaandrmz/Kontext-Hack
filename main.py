#!/usr/bin/env python3
"""
Complete Website-to-Podcast Pipeline

This script orchestrates the entire workflow:
1. Crawl and analyze website using Firecrawl + OpenAI
2. Generate viral clips with app mentions from podcast transcript
3. Create AI-generated podcast videos with lip-sync and captions

Usage:
    python main.py <website_url> <transcript_file> [options]

Required environment variables:
- OPENAI_API_KEY: Your OpenAI API key
- FIRECRAWL_API_KEY: Your Firecrawl API key
- ELEVEN_LABS_KEY: Your ElevenLabs API key
- SYNC_KEY: Your Sync API key
- ZAPCAP_API_KEY: Your ZapCap API key

Install dependencies:
pip install openai requests python-dotenv
"""

import sys
import os
import argparse
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'podcast'))

# Import our custom modules
from website_to_context import crawl_and_analyze_website
from podcast_editor import generate_clips_from_transcript, save_clips_to_file

# Import podcast generation modules
from podcast.script_parser import parse_clips_json
from podcast.audio_generator import generate_all_audio
from podcast.video_generator import generate_all_videos, check_assets
from podcast.video_compiler import compile_podcast


def add_captions_with_zapcap(video_path, output_dir="output"):
    """
    Add captions to the final video using ZapCap API
    (Copied from podcast/main.py for completeness)
    """
    import requests
    import time
    from dotenv import load_dotenv
    
    load_dotenv()
    
    API_KEY = os.getenv('ZAPCAP_API_KEY')
    TEMPLATE_ID = 'e7e758de-4eb4-460f-aeca-b2801ac7f8cc'  # Default fallback
    API_BASE = 'https://api.zapcap.ai'
    
    if not API_KEY:
        raise ValueError("ZAPCAP_API_KEY not found in environment variables")
    
    try:
        # 1. Upload video
        print('📤 Uploading video to ZapCap...')
        with open(video_path, 'rb') as f:
            upload_response = requests.post(
                f'{API_BASE}/videos',
                headers={'x-api-key': API_KEY},
                files={'file': f}
            )
        upload_response.raise_for_status()
        video_id = upload_response.json()['id']
        print(f'✅ Video uploaded, ID: {video_id}')

        # 2. Create captioning task
        print('🔤 Creating captioning task...')
        task_response = requests.post(
            f'{API_BASE}/videos/{video_id}/task',
            headers={
                'x-api-key': API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'templateId': TEMPLATE_ID,
                'autoApprove': True,
                'language': 'en'
            }
        )
        task_response.raise_for_status()
        task_id = task_response.json()['taskId']
        print(f'✅ Task created, ID: {task_id}')

        # 3. Poll for completion
        print('⏳ Processing video (this may take a few minutes)...')
        attempts = 0
        max_attempts = 300  # 10 minutes maximum
        
        while attempts < max_attempts:
            status_response = requests.get(
                f'{API_BASE}/videos/{video_id}/task/{task_id}',
                headers={'x-api-key': API_KEY}
            )
            status_response.raise_for_status()
            data = status_response.json()
            status = data['status']
            
            print(f'Status: {status} (attempt {attempts + 1})')

            if status == 'completed':
                # Download the captioned video
                print('📥 Downloading captioned video...')
                download_response = requests.get(data['downloadUrl'])
                download_response.raise_for_status()

                # Create output filename
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_captioned.mp4")
                
                os.makedirs(output_dir, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(download_response.content)
                    
                print(f'✅ Captioned video saved to: {output_path}')
                return output_path
                
            elif status == 'failed':
                raise Exception(f"ZapCap task failed: {data.get('error')}")

            time.sleep(2)
            attempts += 1

        # If we get here, we've exceeded max attempts
        raise Exception(f"ZapCap processing timed out after {max_attempts} attempts")
        
    except Exception as e:
        print(f'❌ Error during captioning: {str(e)}')
        raise


def full_pipeline(
    website_url: str, 
    transcript_file: str,
    output_dir: str = "output",
    temp_dir: str = "temp",
    clip_index: int = 0,
    clip_max: int = 4,
    whitelist_keywords: Optional[list] = None,
    blacklist_keywords: Optional[list] = None
) -> str:
    """
    Complete pipeline from website URL to final podcast video.
    
    Args:
        website_url (str): URL of the website to analyze
        transcript_file (str): Path to podcast transcript file
        output_dir (str): Directory for final output
        temp_dir (str): Directory for temporary files
        clip_index (int): Which clip to use (0 = top-ranked)
        clip_max (int): Maximum clips to generate
        whitelist_keywords (Optional[list]): Keywords to prioritize
        blacklist_keywords (Optional[list]): Keywords to avoid
        
    Returns:
        str: Path to final video file
    """
    
    print("🚀 STARTING COMPLETE WEBSITE-TO-PODCAST PIPELINE")
    print("=" * 60)
    
    # Step 1: Website Analysis
    print("\n🌐 Step 1: Analyzing website...")
    print(f"URL: {website_url}")
    
    app_analysis = crawl_and_analyze_website(website_url)
    if not app_analysis:
        raise Exception("Failed to analyze website")
    
    print(f"✅ Website analyzed: {app_analysis.get('app_name', 'Unknown App')}")
    print(f"   Value prop: {app_analysis.get('what_it_does', 'N/A')[:100]}...")
    
    # Step 2: Load transcript
    print(f"\n📜 Step 2: Loading transcript...")
    print(f"File: {transcript_file}")
    
    if not os.path.exists(transcript_file):
        raise Exception(f"Transcript file not found: {transcript_file}")
    
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript_content = f.read()
    
    print(f"✅ Transcript loaded ({len(transcript_content)} characters)")
    
    # Step 3: Generate clips with app mentions
    print(f"\n🎬 Step 3: Generating viral clips with app mentions...")
    
    clips_result = generate_clips_from_transcript(
        app_analysis=app_analysis,
        transcript=transcript_content,
        clip_max=clip_max,
        whitelist_keywords=whitelist_keywords,
        blacklist_keywords=blacklist_keywords
    )
    
    if not clips_result or not clips_result.get('clips_ranked'):
        raise Exception("Failed to generate clips")
    
    clips_count = len(clips_result['clips_ranked'])
    print(f"✅ Generated {clips_count} viral clips")
    
    # Save clips for debugging
    clips_file = os.path.join(temp_dir, "generated_clips.json")
    os.makedirs(temp_dir, exist_ok=True)
    save_clips_to_file(clips_result, clips_file)
    print(f"📄 Clips saved to: {clips_file}")
    
    # Validate clip index
    if clip_index >= clips_count:
        print(f"⚠️  Warning: Clip index {clip_index} not available, using 0")
        clip_index = 0
    
    selected_clip = clips_result['clips_ranked'][clip_index]
    print(f"🎯 Selected clip {clip_index} (Rank {selected_clip.get('rank', 'N/A')}):")
    print(f"   Relevance: {selected_clip.get('relevance_score_0_1', 0):.2f}")
    print(f"   Hook: {selected_clip.get('hook_text', 'N/A')[:80]}...")
    
    # Step 4: Check video assets
    print(f"\n📹 Step 4: Checking video assets...")
    if not check_assets():
        print("❌ Please add speaker video files to podcast/assets/ directory")
        print("Required files:")
        print("  - podcast/assets/person1_base.mp4")
        print("  - podcast/assets/person2_base.mp4")
        raise Exception("Missing video assets")
    
    # Step 5: Convert clip to script segments
    print(f"\n📝 Step 5: Converting clip to script segments...")
    
    segments = parse_clips_json(clips_result, clip_index)
    print(f"✅ Converted to {len(segments)} script segments")
    
    for i, segment in enumerate(segments):
        print(f"  {i+1}. {segment['speaker']}: {segment['text'][:50]}...")
    
    # Step 6: Generate audio
    print(f"\n🔊 Step 6: Generating audio with ElevenLabs...")
    audio_files = generate_all_audio(segments, temp_dir)
    print(f"✅ Generated {len(audio_files)} audio files")
    
    # Step 7: Generate videos
    print(f"\n🎬 Step 7: Creating lip-synced videos with Sync API...")
    video_files = generate_all_videos(audio_files, temp_dir)
    print(f"✅ Generated {len(video_files)} video clips")
    
    # Step 8: Compile final podcast
    print(f"\n🎯 Step 8: Compiling final podcast...")
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    app_name_clean = app_analysis.get('app_name', 'app').replace(' ', '_').lower()
    output_name = f"{app_name_clean}_clip_{clip_index}_{timestamp}.mp4"
    
    compiled_video_path = compile_podcast(video_files, output_dir, output_name)
    print(f"✅ Compiled video saved to: {compiled_video_path}")
    
    # Step 9: Add captions with ZapCap
    print(f"\n📝 Step 9: Adding captions with ZapCap...")
    try:
        captioned_video_path = add_captions_with_zapcap(compiled_video_path, output_dir)
        final_path = captioned_video_path
        print(f"✅ Final captioned video: {final_path}")
    except Exception as e:
        print(f"⚠️  Warning: Captioning failed - {e}")
        print(f"📁 Using non-captioned video as final output: {compiled_video_path}")
        final_path = compiled_video_path
    
    return final_path


def main():
    parser = argparse.ArgumentParser(description='Complete Website-to-Podcast Pipeline')
    parser.add_argument('website_url', help='URL of website to analyze')
    parser.add_argument('transcript_file', help='Path to podcast transcript file')
    parser.add_argument('--output-dir', default='output', help='Output directory for final podcast')
    parser.add_argument('--temp-dir', default='temp', help='Temporary directory for processing')
    parser.add_argument('--clip-index', type=int, default=0, help='Which clip to use (0 = top-ranked)')
    parser.add_argument('--clip-max', type=int, default=4, help='Maximum clips to generate')
    parser.add_argument('--whitelist-keywords', nargs='*', help='Keywords to prioritize')
    parser.add_argument('--blacklist-keywords', nargs='*', help='Keywords to avoid')
    parser.add_argument('--save-analysis', action='store_true', help='Save website analysis to file')
    parser.add_argument('--save-clips', action='store_true', help='Save generated clips to file')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.website_url.startswith(('http://', 'https://')):
        print("❌ Please provide a valid URL (must start with http:// or https://)")
        sys.exit(1)
    
    if not os.path.exists(args.transcript_file):
        print(f"❌ Transcript file not found: {args.transcript_file}")
        sys.exit(1)
    
    # Create output directories
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.temp_dir, exist_ok=True)
    
    print("🎙️  WEBSITE-TO-PODCAST PIPELINE")
    print("=" * 60)
    print(f"Website: {args.website_url}")
    print(f"Transcript: {args.transcript_file}")
    print(f"Output Dir: {args.output_dir}")
    print(f"Clip Index: {args.clip_index}")
    print("=" * 60)
    
    try:
        final_video_path = full_pipeline(
            website_url=args.website_url,
            transcript_file=args.transcript_file,
            output_dir=args.output_dir,
            temp_dir=args.temp_dir,
            clip_index=args.clip_index,
            clip_max=args.clip_max,
            whitelist_keywords=args.whitelist_keywords,
            blacklist_keywords=args.blacklist_keywords
        )
        
        print("\n" + "=" * 60)
        print("🎉 PIPELINE COMPLETE!")
        print(f"📁 Final podcast video: {final_video_path}")
        print("=" * 60)
        
        # Optional: Clean up temp files
        cleanup = input("\nClean up temporary files? (y/N): ").strip().lower()
        if cleanup == 'y':
            import shutil
            if os.path.exists(args.temp_dir):
                shutil.rmtree(args.temp_dir)
                print(f"🗑️  Cleaned up {args.temp_dir}/")
        
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        print("\nFor debugging, check:")
        print("1. All API keys are set in your .env file")
        print("2. Website URL is accessible")
        print("3. Transcript file exists and is readable") 
        print("4. Speaker videos exist in podcast/assets/ directory")
        sys.exit(1)


def create_sample_transcript():
    """Create a sample transcript for testing"""
    sample_content = """00:00:00 Speaker A: You know what's frustrating about staying healthy?
00:00:05 Speaker B: What do you mean?
00:00:07 Speaker A: Like, everyone talks about tracking calories, but who has time to log every single thing you eat?
00:00:12 Speaker B: Oh man, totally. I tried that once and gave up after like three days.
00:00:16 Speaker A: Right? It's like a part-time job. You're there with your phone calculator doing math for a sandwich.
00:00:22 Speaker B: And then you're guessing portion sizes anyway, so what's the point?
00:00:26 Speaker A: Exactly! That's why I love when technology actually solves real problems.
00:00:30 Speaker B: What do you mean by that?
00:00:32 Speaker A: Like, imagine if you could just take a picture of your food and get all the nutrition info instantly.
00:00:37 Speaker B: That would be game-changing. Is that even possible?
00:00:40 Speaker A: I mean, AI is getting pretty crazy these days. Computer vision, machine learning...
00:00:45 Speaker B: True, but food is so complex. Different ingredients, cooking methods, portion sizes.
00:00:50 Speaker A: Yeah, but if someone cracked that problem, it would help millions of people stay consistent with their health goals.
00:00:56 Speaker B: For real. Consistency is everything when it comes to nutrition.
00:01:00 Speaker A: And most people fail because tracking is too tedious, not because they don't want to be healthy.
00:01:05 Speaker B: That's a great point. Remove the friction, and people will actually stick with it."""

    with open('sample_transcript.txt', 'w') as f:
        f.write(sample_content)
    
    print("📝 Sample transcript created: sample_transcript.txt")
    print("You can test the pipeline with:")
    print("  python main.py https://www.calai.app/ sample_transcript.txt")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("🎙️  Website-to-Podcast Pipeline")
        print("\nUsage:")
        print("  python main.py <website_url> <transcript_file> [options]")
        print("\nExample:")
        print("  python main.py https://www.calai.app/ transcript.txt")
        print("  python main.py https://example.com/ transcript.txt --clip-index 1")
        print("\nOptions:")
        print("  --clip-index INDEX       Select specific clip (0 = top-ranked)")
        print("  --clip-max COUNT         Maximum clips to generate (default: 4)")
        print("  --output-dir DIR         Output directory (default: output)")
        print("  --whitelist-keywords     Keywords to prioritize")
        print("  --blacklist-keywords     Keywords to avoid")
        print("  --save-analysis          Save website analysis to file")
        print("  --save-clips             Save generated clips to file")
        print("  --help                   Show all options")
        print("\nSetup:")
        print("  1. Set API keys in .env file")
        print("  2. Add speaker videos to podcast/assets/")
        print("  3. pip install openai requests python-dotenv")
        
        if input("\nCreate sample transcript? (y/N): ").strip().lower() == 'y':
            create_sample_transcript()
    elif '--create-sample' in sys.argv:
        create_sample_transcript()
    else:
        main()
