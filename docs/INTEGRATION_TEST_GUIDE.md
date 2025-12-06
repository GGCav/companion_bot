# Integration Test Script - Usage Guide

## Overview
The full integration test script (`scripts/test_full_integration.py`) provides comprehensive testing of all major companion bot components with detailed latency monitoring.

## Components Tested
- ✅ **Memory System**: User profiles, conversation history, preferences
- ✅ **LLM**: Ollama-based conversation with emotion extraction
- ✅ **TTS**: Text-to-speech with emotion modulation (Piper/pyttsx3)
- ✅ **Expression Display**: piTFT emotion display with transitions
- ⏭️ **STT**: Speech-to-text (ready but not active in text mode)
- ⏭️ **Camera**: Face recognition (not yet integrated)
- ⏭️ **Touch Sensors**: Touch interaction (not yet integrated)

## Installation

### Install colorama (if not already installed)
```bash
pip install colorama
```

Or install all requirements:
```bash
cd ~/companion_bot
pip install -r requirements.txt
```

## Running the Test

### Basic Usage
```bash
cd ~/companion_bot
python scripts/test_full_integration.py
```

### Expected Output
```
Initializing components...
  ✅ Memory System (user_id: 1)
  ✅ LLM (qwen2.5:0.5b) - Status: OK
  ✅ TTS (piper)
  ✅ Expression Display
All components initialized!

======================================================================
🤖 COMPANION BOT - FULL INTEGRATION TEST
======================================================================

Test Mode: Interactive Demo
Session ID: 123e4567-e89b-12d3-a456-426614174000

Commands:
  - Type your message to chat
  - Type 'stats' to see latency statistics
  - Type 'quit' or 'exit' to finish and save report
──────────────────────────────────────────────────────────────────────

You: Hello! How are you?
[Processing...]
Bot: [happy] Hi there! I'm doing great! So happy to see you!
[End-to-End: 3.42s]

You: stats
======================================================================
📊 LATENCY STATISTICS
======================================================================

End-to-End Latency:
  Average: 3.420s
  Min: 3.420s | Max: 3.420s | P95: 3.420s | Count: 1

Perceived Latency (to first audio):
  Average: 2.150s
  Min: 2.150s | Max: 2.150s | P95: 2.150s

Component Breakdown:
  memory_context_retrieval      :  0.045s (min: 0.045s, max: 0.045s)
  llm_total                     :  1.823s (min: 1.823s, max: 1.823s)
  llm_time_to_first_token       :  0.876s (min: 0.876s, max: 0.876s)
  tts_total                     :  1.270s (min: 1.270s, max: 1.270s)
  expression_update             :  0.012s (min: 0.012s, max: 0.012s)
  memory_save_message           :  0.038s (min: 0.038s, max: 0.038s)

──────────────────────────────────────────────────────────────────────

You: quit

======================================================================
Report saved to: data/logs/integration_test_report.json
======================================================================
```

## Interactive Commands

### Chat
Simply type your message and press Enter:
```
You: Tell me a story!
```

### View Statistics
Type `stats` to see current latency metrics:
```
You: stats
```

### Exit Test
Type `quit` or `exit` to finish:
```
You: quit
```

Or press `Ctrl+C` to interrupt.

## Latency Metrics Explained

### End-to-End Latency
Total time from when you send a message to when the bot finishes speaking.

**Formula**: `End-to-End = Memory Load + LLM + TTS + Expression`

**Target**: <5 seconds on Raspberry Pi 4

### Perceived Latency
Time from message submission to when the first audio starts playing.

**Formula**: `Perceived = Memory Load + LLM (to first segment)`

**Target**: <3 seconds (with streaming enabled)

### Component Breakdown

| Component | Description | Expected Time |
|-----------|-------------|---------------|
| `memory_context_retrieval` | Load recent conversation history | <0.1s |
| `llm_time_to_first_token` | LLM generates first token | 0.5-1.5s |
| `llm_total` | Complete LLM response generation | 2-5s |
| `tts_total` | All speech synthesis | 0.5-2s/segment |
| `expression_update` | Update piTFT display | <0.05s |
| `memory_save_message` | Save to database | <0.1s |

## JSON Report

After each test session, a detailed JSON report is saved to:
```
data/logs/integration_test_report.json
```

### Report Structure
```json
{
  "test_info": {
    "timestamp": "2025-12-05T17:30:00",
    "session_id": "abc123",
    "user_id": 1,
    "conversation_count": 5,
    "components_tested": ["Memory", "LLM", "TTS", "Expression"]
  },
  "latency_metrics": {
    "end_to_end_latency": {
      "min": 2.5,
      "max": 4.2,
      "avg": 3.1,
      "p95": 3.8,
      "count": 5,
      "total": 15.5
    },
    "llm_time_to_first_token": {
      "min": 0.6,
      "max": 1.2,
      "avg": 0.85,
      "p95": 1.1,
      "count": 5,
      "total": 4.25
    }
    // ... more metrics
  },
  "component_status": {
    "memory": "OK",
    "llm": "OK",
    "tts": "OK",
    "expression": "OK"
  },
  "configuration": {
    "llm_model": "qwen2.5:0.5b",
    "tts_provider": "piper",
    "streaming_enabled": true
  }
}
```

## Troubleshooting

### "Ollama unavailable"
**Solution**: Start Ollama service
```bash
systemctl start ollama
# or
ollama serve
```

### "Expression display failed"
**Symptom**: Script continues with warning
**Impact**: Non-critical, conversation works without display
**Solution**: Check piTFT configuration in `config/settings.yaml`

### "Memory initialization failed"
**Solution**: Ensure `data/` directory exists and is writable
```bash
mkdir -p ~/companion_bot/data/logs
```

### Low performance / High latency
**Potential causes**:
- Ollama model too large for Pi (try `qwen2.5:0.5b` or smaller)
- Multiple heavy processes running
- Insufficient memory/swap

**Check system resources**:
```bash
htop  # Monitor CPU/RAM
free -h  # Check available memory
```

## Performance Optimization Tips

### 1. Enable LLM Streaming
In `config/settings.yaml`:
```yaml
llm:
  streaming:
    enabled: true  # Reduces perceived latency
```

### 2. Reduce Context Window
```yaml
memory:
  conversation:
    context_window: 5  # Default: 10 (fewer = faster)
```

### 3. Use Faster TTS Provider
```yaml
speech:
  tts:
    provider: "pyttsx3"  # Faster but lower quality than Piper
```

### 4. Smaller LLM Model
```yaml
llm:
  ollama:
    model: "qwen2.5:0.5b"  # Lightweight for Pi
```

## Integration with Main Bot

This test script uses the same components as the main companion bot. After testing, you can integrate the conversation pipeline into your main bot:

```python
from llm import ConversationManager, TTSEngine
from expression import EmotionDisplay
from memory import initialize_memory

# Initialize components
user_memory, conversation_history = initialize_memory(config)
conversation_manager = ConversationManager(config, user_memory, conversation_history)
tts_engine = TTSEngine(config)
emotion_display = EmotionDisplay(config)

# Start expression display
emotion_display.start()

# Process user input
response, metadata = conversation_manager.process_user_input("Hello!")
emotion = metadata['emotion']

# Update display and speak
emotion_display.set_emotion(emotion)
emotion_display.set_speaking(True)
tts_engine.speak(response, emotion=emotion, wait=True)
emotion_display.set_speaking(False)
```

## Next Steps

After successful integration testing:
1. Test with voice input (use `VoicePipeline` instead of text)
2. Add camera integration for face recognition
3. Add touch sensor integration
4. Create full companion bot main loop
5. Add startup/shutdown scripts
6. Configure systemd service for auto-start

## Support

For issues or questions:
- Check logs in `data/logs/companion.log`
- Review configuration in `config/settings.yaml`
- See documentation in `docs/`
