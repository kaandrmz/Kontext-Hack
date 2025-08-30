import os
import ffmpeg
import subprocess
from datetime import datetime

def compile_podcast(video_files, output_dir="output", output_name=None):
    """
    Compile all video segments into a single podcast video
    
    Args:
        video_files (list): List of video file info from video_generator
        output_dir (str): Directory to save final podcast
        output_name (str): Optional custom output filename
    
    Returns:
        str: Path to compiled podcast video
    """
    os.makedirs(output_dir, exist_ok=True)
    
    if not video_files:
        raise ValueError("No video files provided for compilation")
    
    if not output_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"podcast_{timestamp}.mp4"
    
    output_path = os.path.join(output_dir, output_name)
    
    try:
        print(f"Compiling {len(video_files)} video segments using the concat filter...")
        
        input_args = []
        scaling_parts = []
        concat_inputs = []
        sorted_videos = sorted(video_files, key=lambda x: x['segment_index'])

        # Define a target resolution to standardize all clips
        target_width = 720
        target_height = 1280

        for i, video_info in enumerate(sorted_videos):
            input_args.extend(['-i', os.path.abspath(video_info['video_path'])])
            # Scale and pad each video to the target resolution, then set SAR
            scaling_parts.append(f"[{i}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v{i}]")
            concat_inputs.append(f"[v{i}][{i}:a:0]")
            
        num_segments = len(video_files)
        filter_complex_str = ";".join(scaling_parts) + ";" + "".join(concat_inputs) + f"concat=n={num_segments}:v=1:a=1[outv][outa]"

        command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
        ]
        command.extend(input_args)
        command.extend([
            '-filter_complex', filter_complex_str,
            '-map', '[outv]',
            '-map', '[outa]',
            output_path
        ])
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"✅ Podcast compiled successfully: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error during compilation:")
        print(f"Command: {' '.join(command)}")
        print(f"Stderr: {e.stderr}")
        raise
    except Exception as e:
        print(f"❌ Error during compilation: {e}")
        raise

def compile_with_custom_settings(video_files, output_dir="output", output_name=None, **kwargs):
    """
    Compile podcast with custom FFmpeg settings
    
    Args:
        video_files (list): List of video file info
        output_dir (str): Output directory
        output_name (str): Output filename
        **kwargs: Additional FFmpeg parameters
    
    Returns:
        str: Path to compiled video
    """
    os.makedirs(output_dir, exist_ok=True)
    
    if not output_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"podcast_custom_{timestamp}.mp4"
    
    output_path = os.path.join(output_dir, output_name)
    
    try:
        print(f"Compiling {len(video_files)} video segments with custom settings using the concat filter...")

        input_args = []
        scaling_parts = []
        concat_inputs = []
        sorted_videos = sorted(video_files, key=lambda x: x['segment_index'])
        
        # Define a target resolution to standardize all clips
        target_width = 720
        target_height = 1280

        for i, video_info in enumerate(sorted_videos):
            input_args.extend(['-i', os.path.abspath(video_info['video_path'])])
            # Scale and pad each video to the target resolution, then set SAR
            scaling_parts.append(f"[{i}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v{i}]")
            concat_inputs.append(f"[v{i}][{i}:a:0]")
        
        num_segments = len(video_files)
        filter_complex_str = ";".join(scaling_parts) + ";" + "".join(concat_inputs) + f"concat=n={num_segments}:v=1:a=1[outv][outa]"

        command = [
            'ffmpeg',
            '-y',
        ]
        command.extend(input_args)
        command.extend([
            '-filter_complex', filter_complex_str,
            '-map', '[outv]',
            '-map', '[outa]',
        ])

        for key, value in kwargs.items():
            command.extend([f'-{key}', str(value)])
        
        command.append(output_path)
        
        subprocess.run(command, capture_output=True, text=True, check=True)
        
        print(f"✅ Custom compilation complete: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error in custom compilation:")
        print(f"Command: {' '.join(command)}")
        print(f"Stderr: {e.stderr}")
        raise
    except Exception as e:
        print(f"❌ Error in custom compilation: {e}")
        raise

def get_video_info(video_path):
    """Get information about a video file using FFmpeg"""
    try:
        probe = ffmpeg.probe(video_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        
        return {
            'duration': float(probe['format']['duration']),
            'width': int(video_info['width']),
            'height': int(video_info['height']),
            'fps': eval(video_info['r_frame_rate']),
            'codec': video_info['codec_name']
        }
    except Exception as e:
        print(f"Error getting video info for {video_path}: {e}")
        return None

if __name__ == "__main__":
    # Test with sample video files
    sample_video_files = [
        {
            'segment_index': 0,
            'speaker': 'person1',
            'video_path': 'temp/person1_974_synced.mp4'
        },
        {
            'segment_index': 1, 
            'speaker': 'person2',
            'video_path': 'temp/person2_5279_synced.mp4'
        },
        {
            'segment_index': 2,
            'speaker': 'person1',
            'video_path': 'temp/person1_8594_synced.mp4'
        },
        {
            'segment_index': 3,
            'speaker': 'person2', 
            'video_path': 'temp/person2_5519_synced.mp4'
        },
        {
            'segment_index': 4,
            'speaker': 'person1',
            'video_path': 'temp/person1_3737_synced.mp4'
        },
        {
            'segment_index': 5,
            'speaker': 'person2',
            'video_path': 'temp/person2_9564_synced.mp4'
        },
        {
            'segment_index': 6,
            'speaker': 'person1',
            'video_path': 'temp/person1_4458_synced.mp4'
        },
        {
            'segment_index': 7,
            'speaker': 'person2',
            'video_path': 'temp/person2_3930_synced.mp4'
        },
        {
            'segment_index': 8,
            'speaker': 'person1',
            'video_path': 'temp/person1_7456_synced.mp4'
        }
    ]
    
    # Check if sample files exist
    print("Checking for sample video files...")
    existing_files = []
    for vf in sample_video_files:
        if os.path.exists(vf['video_path']):
            print(f"  [FOUND] {vf['video_path']}")
            existing_files.append(vf)
        else:
            print(f"  [MISSING] {vf['video_path']}")

    if existing_files:
        print("\nTesting video compilation...")
        output_path = compile_podcast(existing_files, output_name="test_podcast.mp4")
        print(f"Test compilation saved to: {output_path}")
    else:
        print("\nNo sample video files found for testing.")
        print("Please ensure the sample video files exist in the 'temp' directory.")
        print("This module is intended to be used after video generation is complete.")
