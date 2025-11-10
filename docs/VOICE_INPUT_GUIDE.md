# Voice Input Guide - Mini Microphone + Whisper

Complete guide for using voice input with mini microphone and OpenAI Whisper on Raspberry Pi.

## Overview

The voice input system consists of three integrated components:

1. **Audio Input** - Captures audio from mini microphone with voice activity detection
2. **STT Engine** - Transcribes speech using OpenAI Whisper
3. **Voice Pipeline** - Orchestrates the complete flow from microphone to text

```
Mini Microphone → VAD → Whisper → Text Output
```

## Quick Start

### 1. Test Your Setup

```bash
cd companion_bot
source venv/bin/activate
python scripts/test_voice_input.py
```

This will:
- Check if microphone is detected
- Test audio levels
- Listen for speech
- Transcribe what you say

### 2. Basic Usage in Code

```python
import yaml
from llm.voice_pipeline import VoicePipeline

# Load config
with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

# Create pipeline
pipeline = VoicePipeline(config)

# Set callback
def on_transcription(result):
    print(f"You said: {result['text']}")

pipeline.set_transcription_callback(on_transcription)

# Start listening
pipeline.start()

# Keep running...
try:
    while True:
        time.sleep(0.1)
finally:
    pipeline.cleanup()
```

## Architecture

### Component Breakdown

#### 1. AudioInput (`src/audio/audio_input.py`)
- Captures raw audio from mini microphone
- Handles USB and I2S microphones
- Provides audio level monitoring
- Threaded for non-blocking operation

**Key Features:**
- Configurable sample rate (16kHz default, optimal for Whisper)
- Voice Activity Detection (VAD)
- Automatic silence detection
- Audio normalization for quiet microphones

#### 2. STTEngine (`src/llm/stt_engine.py`)
- OpenAI Whisper integration
- Multiple model sizes: tiny, base, small
- Optimized for Raspberry Pi CPU
- Real-time transcription with preprocessing

**Key Features:**
- Automatic audio normalization
- Noise reduction for mini mics
- Language detection (99 languages)
- Confidence scoring
- Performance tracking

#### 3. VoicePipeline (`src/llm/voice_pipeline.py`)
- End-to-end orchestration
- Automatic speech detection
- Callback-based events
- Statistics tracking

**Key Features:**
- Non-blocking operation
- Automatic speech segmentation
- Event callbacks (speech start/end, transcription)
- Queue-based transcription retrieval

## Configuration

### Audio Settings (`config/settings.yaml`)

```yaml
audio:
  input:
    device_index: null  # null = default, or specific device number
    channels: 1         # Mini mics are typically mono
    sample_rate: 16000  # Optimal for Whisper
    chunk_size: 1024    # Audio buffer size

  processing:
    noise_reduction: true
    auto_gain: true
    vad_aggressiveness: 2  # 0-3, higher = more aggressive
    silence_threshold: 500  # Amplitude threshold
    silence_duration: 1.5   # Seconds before stopping
```

### Whisper Settings

```yaml
speech:
  stt:
    provider: "whisper"
    language: "en"  # or "auto" for detection

    whisper:
      model_size: "base"  # tiny, base, small, medium, large
      device: "cpu"       # cpu or cuda
```

### Model Size Comparison

| Model | Size | Speed (Pi 4) | Accuracy | Use Case |
|-------|------|--------------|----------|----------|
| `tiny` | 39 MB | ~2s | Good | Testing, fast response |
| `base` | 74 MB | ~5s | Better | **Recommended for Pi** |
| `small` | 244 MB | ~15s | Best | High accuracy needed |

## Mini Microphone Optimization

### Common Issues & Solutions

#### Issue: Low Volume / Not Detected

**Solution 1: Increase System Volume**
```bash
alsamixer
# Press F6 to select sound card
# Adjust "Mic" and "Capture" levels
```

**Solution 2: Enable Auto-Gain**
```yaml
audio:
  processing:
    auto_gain: true
```

**Solution 3: Test Microphone**
```bash
# List devices
arecord -l

# Test recording (device hw:1,0)
arecord -D hw:1,0 -f S16_LE -r 16000 -d 5 test.wav
aplay test.wav
```

#### Issue: High Background Noise

**Solution: Enable Noise Reduction**
```yaml
audio:
  processing:
    noise_reduction: true
    vad_aggressiveness: 3  # More aggressive filtering
```

#### Issue: Speech Cut Off Too Early

**Solution: Increase Silence Duration**
```yaml
audio:
  processing:
    silence_duration: 2.5  # Wait longer before stopping
```

#### Issue: Too Sensitive (Activates on Background Noise)

**Solution: Increase Thresholds**
```yaml
audio:
  processing:
    vad_aggressiveness: 1  # Less sensitive
    silence_threshold: 800  # Higher threshold
```

## Advanced Usage

### Custom Transcription Callback

```python
def on_transcription(result):
    text = result['text']
    confidence = result['confidence']
    language = result['language']
    duration = result['duration']

    # Check confidence
    if confidence > 0.8:
        print(f"High confidence: {text}")
        # Process command
    else:
        print(f"Low confidence: {text} (might be wrong)")
```

### Speech Event Callbacks

```python
def on_speech_start():
    # Visual indicator (e.g., LED on)
    print("🎤 Listening...")

def on_speech_end():
    # Visual indicator (e.g., LED off)
    print("🔇 Processing...")

pipeline.set_speech_callbacks(on_speech_start, on_speech_end)
```

### Blocking Wait for Transcription

```python
pipeline.start()

# Wait for next transcription (blocks up to 30s)
result = pipeline.wait_for_transcription(timeout=30.0)

if result:
    print(f"You said: {result['text']}")
else:
    print("No speech detected")
```

### Non-Blocking Check

```python
while True:
    # Check for transcription without blocking
    result = pipeline.get_transcription(timeout=0.1)

    if result:
        print(f"Transcribed: {result['text']}")

    # Do other work...
    time.sleep(0.1)
```

### Multiple Language Support

```python
# Detect language automatically
stt_engine.change_language('auto')

# Or set specific language
stt_engine.change_language('es')  # Spanish
stt_engine.change_language('fr')  # French
stt_engine.change_language('ja')  # Japanese

# Get supported languages
languages = stt_engine.get_supported_languages()
print(f"Supports {len(languages)} languages")
```

### Performance Monitoring

```python
stats = pipeline.get_statistics()

print(f"Total utterances: {stats['total_utterances']}")
print(f"Avg time: {stats['avg_transcription_time']:.2f}s")
print(f"Last time: {stats['last_transcription_time']:.2f}s")

# STT engine stats
stt_stats = stats['stt_stats']
print(f"Model: {stt_stats['model_size']}")
print(f"Device: {stt_stats['device']}")
print(f"Avg confidence: {stt_stats['avg_confidence']:.2%}")
```

## Performance Tuning

### For Faster Response

```yaml
speech:
  stt:
    whisper:
      model_size: "tiny"  # Fastest model
```

### For Better Accuracy

```yaml
speech:
  stt:
    whisper:
      model_size: "small"  # More accurate
```

### For Noisy Environments

```yaml
audio:
  processing:
    noise_reduction: true
    vad_aggressiveness: 3
    silence_threshold: 1000  # Higher threshold
```

### For Quiet Speakers

```yaml
audio:
  processing:
    auto_gain: true
    vad_aggressiveness: 1  # Less aggressive
    silence_threshold: 300  # Lower threshold
```

## Integration Examples

### Example 1: Simple Voice Commands

```python
from llm.voice_pipeline import VoicePipeline
import yaml

config = yaml.safe_load(open('config/settings.yaml'))
pipeline = VoicePipeline(config)

COMMANDS = {
    'hello': 'greet',
    'play': 'play_action',
    'stop': 'stop_action',
    'sleep': 'sleep_mode'
}

def on_transcription(result):
    text = result['text'].lower()

    for keyword, action in COMMANDS.items():
        if keyword in text:
            print(f"Command detected: {action}")
            # Execute action
            break

pipeline.set_transcription_callback(on_transcription)
pipeline.start()
```

### Example 2: Conversation Mode

```python
from llm.voice_pipeline import VoicePipeline
from llm.ollama_client import OllamaClient  # To be implemented

pipeline = VoicePipeline(config)
llm = OllamaClient(config)

def on_transcription(result):
    user_input = result['text']
    print(f"User: {user_input}")

    # Get LLM response
    response = llm.generate(user_input)
    print(f"Bot: {response}")

    # Speak response (TTS)
    # tts.speak(response)

pipeline.set_transcription_callback(on_transcription)
pipeline.start()
```

### Example 3: Wake Word Detection

```python
from llm.voice_pipeline import VoicePipeline

pipeline = VoicePipeline(config)
wake_word = "hey buddy"
is_active = False

def on_transcription(result):
    global is_active
    text = result['text'].lower()

    if not is_active:
        # Wait for wake word
        if wake_word in text:
            is_active = True
            print("🤖 Activated! Listening for command...")
    else:
        # Process command
        print(f"Command: {text}")
        # Process...
        is_active = False  # Deactivate after command

pipeline.set_transcription_callback(on_transcription)
pipeline.start()
```

## Troubleshooting

### No Audio Devices Found

```bash
# Check USB devices
lsusb

# Check ALSA devices
arecord -l
aplay -l

# Restart ALSA
sudo alsa force-reload
```

### Permission Denied

```bash
# Add user to audio group
sudo usermod -a -G audio $USER
sudo reboot
```

### Whisper Model Download Fails

```bash
# Manual download
python -c "import whisper; whisper.load_model('base')"

# Or download to specific location
mkdir -p ~/.cache/whisper
cd ~/.cache/whisper
wget https://openaipublic.azureedge.net/main/whisper/models/...
```

### Poor Transcription Quality

1. **Check microphone distance**: Speak 10-30cm from mic
2. **Reduce background noise**: Close windows, turn off fans
3. **Speak clearly**: Avoid mumbling, speak at normal pace
4. **Check audio levels**: Use `alsamixer` to adjust
5. **Try different model**: Switch to `small` for better accuracy

### High CPU Usage

1. **Use smaller model**: Switch from `base` to `tiny`
2. **Reduce sample rate**: Change to 8000 Hz (lower quality)
3. **Increase chunk size**: Larger buffers = less processing
4. **Optimize Pi**: Overclock, disable desktop environment

## Best Practices

1. **Position microphone properly**
   - 10-30cm from speaker's mouth
   - Away from noise sources
   - Stable mounting

2. **Optimize for environment**
   - Adjust VAD settings based on noise level
   - Use noise reduction in noisy environments
   - Test different model sizes

3. **Handle errors gracefully**
   - Check transcription confidence
   - Provide feedback (visual/audio)
   - Allow retries

4. **Monitor performance**
   - Track transcription times
   - Log errors and issues
   - Adjust settings based on stats

## Testing Checklist

- [ ] Microphone detected (`arecord -l`)
- [ ] Audio levels good (`alsamixer`)
- [ ] Test recording works (`arecord`/`aplay`)
- [ ] Voice pipeline initializes
- [ ] Speech detection works
- [ ] Transcription accurate
- [ ] Performance acceptable (<5s for base model)
- [ ] No memory leaks over time

## Support & Resources

- **Whisper Documentation**: https://github.com/openai/whisper
- **Raspberry Pi Audio**: https://www.raspberrypi.com/documentation/computers/configuration.html#audio-configuration
- **ALSA Guide**: https://alsa-project.org/wiki/Main_Page

---

**Need Help?**
- Check logs: `data/logs/companion.log`
- Run test: `python scripts/test_voice_input.py`
- Verify config: `config/settings.yaml`

---

**Last Updated:** November 2025
**Optimized for:** Mini USB Microphone + Raspberry Pi 4 + Whisper Base Model
