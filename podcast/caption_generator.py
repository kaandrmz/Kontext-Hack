#!/usr/bin/env python3
"""
Standalone Video Caption Generator using ZapCap API

Usage:
    python caption_generator.py input_video.mp4 [output_directory]
    
    or as a module:
    from caption_generator import add_captions
    captioned_path = add_captions("input_video.mp4", "output_dir")
"""

import os
import sys
import argparse
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_captions(video_path, output_dir="output", template_id=None):
    """
    Add captions to a video using ZapCap API
    
    Args:
        video_path (str): Path to the input video file
        output_dir (str): Directory to save the captioned video
        template_id (str): Optional template ID to override default
        
    Returns:
        str: Path to the captioned video file
    """
    API_KEY = os.getenv('ZAPCAP_API_KEY')
    TEMPLATE_ID = template_id or os.getenv('ZAPCAP_TEMPLATE_ID', 'ca050348-e2d0-49a7-9c75-7a5e8335c67d')
    API_BASE = 'https://api.zapcap.ai'
    
    # Validate inputs
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if not API_KEY:
        raise ValueError("ZAPCAP_API_KEY not found in environment variables. Please add it to your .env file")
    
    try:
        # 1. Upload video
        print(f'📤 Uploading video: {os.path.basename(video_path)}...')
        with open(video_path, 'rb') as f:
            upload_response = requests.post(
                f'{API_BASE}/videos',
                headers={'x-api-key': API_KEY},
                files={'file': f}
            )
        upload_response.raise_for_status()
        video_id = upload_response.json()['id']
        print(f'✅ Video uploaded successfully, ID: {video_id}')

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
        print(f'✅ Task created successfully, ID: {task_id}')

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
            
            if attempts % 15 == 0:  # Print status every 30 seconds
                print(f'🔄 Status: {status} (attempt {attempts + 1}/{max_attempts})')

            if status == 'completed':
                # Download the captioned video
                print('📥 Downloading captioned video...')
                download_response = requests.get(data['downloadUrl'])
                download_response.raise_for_status()

                # Create output filename
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_captioned.mp4")
                
                # Ensure output directory exists
                os.makedirs(output_dir, exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(download_response.content)
                    
                print(f'✅ Captioned video saved to: {output_path}')
                return output_path
                
            elif status == 'failed':
                error_msg = data.get('error', 'Unknown error')
                raise Exception(f"ZapCap task failed: {error_msg}")

            time.sleep(2)
            attempts += 1

        # If we get here, we've exceeded max attempts
        raise Exception(f"ZapCap processing timed out after {max_attempts} attempts ({max_attempts * 2} seconds)")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Captioning failed: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Add captions to video using ZapCap API')
    parser.add_argument('video_path', help='Path to input video file')
    parser.add_argument('--output-dir', '-o', default='output', 
                       help='Output directory for captioned video (default: output)')
    parser.add_argument('--template-id', '-t', 
                       help='ZapCap template ID (overrides env variable)')
    
    args = parser.parse_args()
    
    print("📝 ZapCap Video Caption Generator")
    print("=" * 40)
    print(f"Input video: {args.video_path}")
    print(f"Output directory: {args.output_dir}")
    print("=" * 40)
    
    try:
        captioned_path = add_captions(
            video_path=args.video_path,
            output_dir=args.output_dir,
            template_id=args.template_id
        )
        
        print("\n" + "=" * 40)
        print("🎉 CAPTIONING COMPLETE!")
        print(f"📁 Captioned video: {captioned_path}")
        print("=" * 40)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your ZAPCAP_API_KEY in .env file")
        print("2. Verify the video file exists and is a valid MP4")
        print("3. Check your internet connection")
        print("4. Ensure you have a valid ZapCap template ID")
        sys.exit(1)

if __name__ == "__main__":
    main()
