import os
import re
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize ElevenLabs client with explicit API key
client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

# Voice ID mappings for different speakers
VOICE_MAPPINGS = {
    'person1': '6OzrBCQf8cjERkYgzSg8',  # Built-in voice: Josh (male). normally use uju3wxzG5OhpWcoi3SMy instead
    'person2': 'VCgLBmBjldJmfphyB8sZ',  # Built-in voice: Sarah (female). normally use jqcCZkN6Knx8BJ5TBdYR instead
}

def generate_audio_for_segment(text, speaker, output_dir="temp"):
    """
    Generate audio for a single text segment using ElevenLabs TTS
    
    Args:
        text (str): Text to convert to speech
        speaker (str): Speaker name (e.g., 'person1')
        output_dir (str): Directory to save audio files
    
    Returns:
        str: Path to generated audio file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Get voice ID for speaker
    voice_id = VOICE_MAPPINGS.get(speaker)
    if not voice_id:
        raise ValueError(f"No voice mapping found for speaker: {speaker}")
    
    # Generate audio using the modern client approach
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_v3",
        output_format="mp3_44100_128",
    )
    
    # Save audio file
    output_path = os.path.join(output_dir, f"{speaker}_{hash(text) % 10000}.mp3")
    
    with open(output_path, 'wb') as f:
        for chunk in audio:
            if isinstance(chunk, bytes):
                f.write(chunk)
    
    return output_path

def generate_all_audio(segments, output_dir="temp"):
    """
    Generate audio for all segments from script parser
    
    Args:
        segments (list): List of segments from script_parser.parse_script()
        output_dir (str): Directory to save audio files
    
    Returns:
        list: List of audio file paths in order
    """
    audio_files = []
    
    for i, segment in enumerate(segments):
        speaker = segment['speaker']
        text = segment['text']
        
        print(f"Generating audio for segment {i+1}: {speaker}")
        print(f"Text: {text[:50]}...")
        
        try:
            audio_path = generate_audio_for_segment(text, speaker, output_dir)
            audio_files.append({
                'segment_index': i,
                'speaker': speaker,
                'text': text,
                'audio_path': audio_path
            })
            print(f"✅ Saved: {audio_path}")
        except Exception as e:
            print(f"❌ Error generating audio for segment {i+1}: {e}")
            raise
    
    return audio_files

def parse_script_file(script_path):
    """
    Parse the sample script file and return segments for audio generation
    
    Args:
        script_path (str): Path to the script file
    
    Returns:
        list: List of segments with speaker and text
    """
    segments = []
    current_speaker = None
    
    with open(script_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Check if line contains speaker marker
        if line.startswith('{') and line.endswith('}'):
            current_speaker = line.strip('{}')
            continue
        
        # If we have a speaker and text, process the line
        if current_speaker and line:
            # Keep the text with all bracketed stage directions and emotional cues
            # These tags help provide context for the TTS system
            text = line.strip()
            
            # Skip if the line is empty
            if not text:
                continue
                
            segments.append({
                'speaker': current_speaker,
                'text': text
            })
    
    return segments

if __name__ == "__main__":
    # Parse sample script file
    script_path = "sample_script.txt"
    
    if not os.path.exists(script_path):
        print(f"❌ Script file not found: {script_path}")
        print("Please ensure sample_script.txt is in the same directory as this script.")
        exit(1)
    
    print(f"📖 Parsing script file: {script_path}")
    segments = parse_script_file(script_path)
    
    print(f"✅ Parsed {len(segments)} segments from script")
    print("\nSegments preview:")
    for i, segment in enumerate(segments[:3]):  # Show first 3 segments
        print(f"{i+1}. {segment['speaker']}: {segment['text'][:60]}...")
    
    print(f"\nGenerating audio for all {len(segments)} segments...")
    audio_files = generate_all_audio(segments)
    
    print(f"\n🎵 Successfully generated {len(audio_files)} audio files:")
    for audio_info in audio_files:
        print(f"  {audio_info['speaker']}: {audio_info['audio_path']}")
