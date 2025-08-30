import os
import time
import requests
from sync import Sync
from sync.common import GenerationOptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Video mappings for different speakers
VIDEO_MAPPINGS = {
    'person1': 'podcast/assets/man_1.mp4',
    'person2': 'podcast/assets/man_2.mp4',
}

def generate_video_for_segment(audio_path, speaker, output_dir="temp"):
    """
    Generate lip-synced video for a single audio segment using Sync API
    
    Args:
        audio_path (str): Path to audio file
        speaker (str): Speaker name (e.g., 'person1')
        output_dir (str): Directory to save video files
    
    Returns:
        str: Path to generated video file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base video for speaker
    base_video_path = VIDEO_MAPPINGS.get(speaker)
    if not base_video_path or not os.path.exists(base_video_path):
        raise ValueError(f"Base video not found for speaker: {speaker} at {base_video_path}")
    
    # Initialize Sync client
    sync_client = Sync()
    
    # Create output path
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_synced.mp4")
    
    try:
        # Generate lip-synced video by uploading files
        with open(base_video_path, "rb") as video_file, open(audio_path, "rb") as audio_file:
            generation = sync_client.generations.create_with_files(
                video=video_file,
                audio=audio_file,
                model="lipsync-2",
                # options=GenerationOptions(
                #     sync_mode="loop",
                # ),
            )

        print(f"✅ Sync generation created for {speaker}")
        generation_id = generation.id if hasattr(generation, 'id') else None
        if not generation_id:
            raise Exception("Failed to get generation ID")
        print(f"Generation ID: {generation_id}")

        # Poll for completion
        while True:
            generation = sync_client.generations.get(id=generation_id)
            status = generation.status
            print(f"Generation status for {speaker}: {status}")

            if status == "COMPLETED":
                video_url = generation.output_url
                if video_url:
                    print(f"Downloading video from {video_url}")
                    response = requests.get(video_url, stream=True)
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"✅ Video saved to {output_path}")
                    return output_path
                else:
                    raise Exception("Generation completed but no video URL found.")

            elif status == "ERROR":
                raise Exception(f"Generation failed with status: {status}")

            time.sleep(10)  # Wait 10 seconds before polling again

    except Exception as e:
        print(f"❌ Error generating video for {speaker}: {e}")
        raise


def generate_all_videos(audio_files, output_dir="temp"):
    """
    Generate lip-synced videos for all audio files
    
    Args:
        audio_files (list): List of audio file info from audio_generator
        output_dir (str): Directory to save video files
    
    Returns:
        list: List of video file paths in order
    """
    video_files = []
    
    for audio_info in audio_files:
        speaker = audio_info['speaker']
        audio_path = audio_info['audio_path']
        segment_index = audio_info['segment_index']
        
        print(f"Generating video for segment {segment_index + 1}: {speaker}")
        
        try:
            video_path = generate_video_for_segment(audio_path, speaker, output_dir)
            video_files.append({
                'segment_index': segment_index,
                'speaker': speaker,
                'audio_path': audio_path,
                'video_path': video_path
            })
            print(f"✅ Video generated: {video_path}")
        except Exception as e:
            print(f"❌ Error generating video for segment {segment_index + 1}: {e}")
            raise
    
    return video_files

def check_assets():
    """Check if all required video assets exist"""
    missing_assets = []
    
    for speaker, video_path in VIDEO_MAPPINGS.items():
        if not os.path.exists(video_path):
            missing_assets.append(f"{speaker}: {video_path}")
    
    if missing_assets:
        print("❌ Missing video assets:")
        for asset in missing_assets:
            print(f"  - {asset}")
        return False
    else:
        print("✅ All video assets found")
        return True

if __name__ == "__main__":
    # Check if video assets exist
    print("Checking video assets...")
    assets_ok = check_assets()
    
    if assets_ok:
        # Test with sample audio files (would come from audio_generator)
        sample_audio_files = [
            {
                'segment_index': 0,
                'speaker': 'person1',
                'audio_path': 'temp/person1_1234.mp3'
            }
        ]
        
        print("Testing video generation...")
        # video_files = generate_all_videos(sample_audio_files)
        print("Video generation test complete")
    else:
        print("Please add your speaker video files to the assets/ directory")
