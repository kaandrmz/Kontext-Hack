# 🎙️ Website-to-Podcast Pipeline

**Complete AI-powered pipeline that transforms websites into viral podcast clips with soft product integration.**

Takes any website and existing podcast transcript, then generates professional podcast videos with lip-sync, captions, and natural app mentions.

## 🚀 Features

- **Website Analysis**: Automatically crawls and analyzes websites using Firecrawl + OpenAI
- **Viral Clip Extraction**: Finds the most engaging 30-second segments from podcast transcripts
- **Soft App Integration**: Naturally weaves product mentions into dialogue 
- **ElevenLabs V3 Enhancement**: Adds emotion tags like `[thoughtful]`, `[excited]` for natural speech
- **Lip-Sync Videos**: Creates realistic talking head videos using Sync API
- **Auto Captions**: Adds professional captions with ZapCap API
- **Complete Automation**: One command generates a full podcast video

## 📋 Prerequisites

### API Keys Required
Create a `.env` file with:
```bash
OPENAI_API_KEY=your_openai_key
FIRECRAWL_API_KEY=your_firecrawl_key
ELEVEN_LABS_KEY=your_elevenlabs_key
SYNC_KEY=your_sync_api_key
ZAPCAP_API_KEY=your_zapcap_key
```

### System Requirements
- **FFmpeg** (for video processing)
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`
  - Windows: Download from https://ffmpeg.org/

### Speaker Videos
Add base speaker videos to `podcast/assets/`:
- `man_1.mp4` - Speaker A video
- `man_2.mp4` - Speaker B video

## 🛠️ Installation

```bash
git clone <repository>
cd Kontext-Hack
uv pip install -r requirements.txt
```

## 🎯 Quick Start

### 1. Complete Pipeline (Website → Video)
```bash
python main.py https://www.example.com/ transcript.txt
```

This will:
1. Analyze the website
2. Extract viral clips from your transcript
3. Add soft product mentions
4. Generate lip-synced video with captions

### 2. Just Extract Clips (No Video)
```bash
python podcast_editor.py
```

Generates enhanced clips JSON with ElevenLabs emotion tags.

### 3. Generate Video from Existing Clips
```bash
python podcast/main.py generated_clips.json --clip-index 0
```

## 💡 Usage Examples

### Basic Usage
```bash
# Complete pipeline
python main.py https://www.calai.app/ my_podcast.txt

# Use specific clip (0 = top-ranked)
python main.py https://example.com/ transcript.txt --clip-index 1

# Custom output directory
python main.py https://example.com/ transcript.txt --output-dir videos/
```

### Advanced Options
```bash
# Control clip generation
python main.py https://example.com/ transcript.txt \
  --clip-max 6 \
  --whitelist-keywords "nutrition, health, tracking" \
  --blacklist-keywords "politics, religion"
```

### Transcript Format
Your transcript should have timestamps and speaker labels:
```
00:00:00 Speaker A: Welcome to our show today!
00:00:05 Speaker B: Thanks for having me.
00:00:08 Speaker A: Let's talk about the challenges in...
```

## 🎨 Customization

### Emotion Prompts
Edit `podcast_editor.py` to customize the enhancement behavior:
```python
# Default: "{emotion prompt}"
# Custom: "Make this more energetic and conversational"
emotion_prompt="Add more excitement and curiosity to the dialogue"
```

### Speaker Voices
Configure ElevenLabs voice IDs in `podcast/audio_generator.py`:
```python
VOICE_MAPPING = {
    'person1': 'your_voice_id_1',
    'person2': 'your_voice_id_2'
}
```

## 🔧 Standalone Components

Each component can be used independently:

**Website Analysis Only:**
```python
from website_to_context import crawl_and_analyze_website
result = crawl_and_analyze_website("https://example.com")
```

**Clip Enhancement Only:**
```python
from podcast_editor import generate_clips_from_transcript
clips = generate_clips_from_transcript(app_analysis, transcript)
```

**Video Generation Only:**
```bash
python podcast/main.py script.txt
```

## 📊 Output

### Clips JSON Structure
```json
{
  "topic": "AI, productivity, automation",
  "audience": "Tech professionals seeking efficiency",
  "clips_ranked": [
    {
      "rank": 1,
      "start_time": "00:01:15",
      "end_time": "00:01:45", 
      "hook_text": "You know what's crazy about...",
      "full_30s_transcript": "Speaker A: [thoughtful] You know what's crazy...",
      "dialogue_lines": [
        {
          "speaker": "Speaker A",
          "text": "[thoughtful] You know what's crazy about productivity apps?"
        }
      ],
      "app_mention_present": true,
      "relevance_score_0_1": 0.95,
      "viral_rationale": { ... }
    }
  ]
}
```

### Final Video
- **Duration**: ~30 seconds per clip
- **Resolution**: 1080p
- **Audio**: ElevenLabs with emotion tags
- **Video**: Lip-synced talking heads
- **Captions**: Auto-generated and styled

## 🐛 Troubleshooting

### Common Issues

**"Missing video assets"**
- Add `person1_base.mp4` and `person2_base.mp4` to `podcast/assets/`

**"API key not found"**
- Check your `.env` file has all required keys
- Ensure `.env` is in the project root directory

**"FFmpeg not found"**
- Install FFmpeg system-wide
- Verify with `ffmpeg -version`

**"No clips generated"**
- Check transcript format (timestamps + speaker labels)
- Verify website is accessible
- Try different whitelist keywords

### Debug Mode
Add `--save-clips` and `--save-analysis` flags to save intermediate files:
```bash
python main.py https://example.com/ transcript.txt --save-clips --save-analysis
```