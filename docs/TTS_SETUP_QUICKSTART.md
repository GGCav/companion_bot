# TTS Setup Quick Start

Quick reference for configuring TTS with wm8960-soundcard.

---

## Prerequisites

✅ TTS Pipeline already implemented (TTSEngine + emotion support)
✅ wm8960-soundcard detected on Raspberry Pi (card 0, device 0)
✅ Speakers connected to wm8960-soundcard

---

## Setup (5 minutes)

### 1. Configure ALSA (on Raspberry Pi)

```bash
# Copy ALSA config
cd ~/companion_bot
sudo cp config/asound.conf /etc/asound.conf

# Reboot
sudo reboot
```

### 2. Test Audio

```bash
# Test speaker output
speaker-test -c 2 -t wav
# Press Ctrl+C after hearing test tone
```

### 3. Test TTS

```bash
cd ~/companion_bot
python scripts/test_tts_hardware.py
```

**Expected**: You should hear:
- Basic speech test
- 12 emotion voices (happy, sad, excited, etc.)
- Multi-emotion speech with transitions

### 4. Adjust Volume (if needed)

```bash
alsamixer
# Press F6, select wm8960-soundcard
# Adjust with arrow keys, ESC to exit
```

---

## Files Created

| File | Purpose |
|------|---------|
| `config/asound.conf` | ALSA configuration for wm8960-soundcard |
| `scripts/test_tts_hardware.py` | Comprehensive TTS test script |
| `docs/AUDIO_SETUP.md` | Complete setup guide with troubleshooting |
| `config/settings.yaml` | Updated with wm8960 documentation |

---

## Verify It Works

Run the full conversation pipeline:

```bash
cd ~/companion_bot
python scripts/demo_full_conversation.py
```

Speak into microphone → Bot responds with voice (via wm8960-soundcard)

---

## Troubleshooting

**No audio?**
```bash
aplay -l                    # Check if wm8960 detected
cat /etc/asound.conf        # Verify config installed
alsamixer                   # Check volume/mute
```

**See full guide**: `docs/AUDIO_SETUP.md`

---

## Architecture

```
User speaks → Whisper STT → Ollama LLM → TTSEngine
                                             ↓
                               (emotion modulation)
                                             ↓
                                      pyttsx3/espeak
                                             ↓
                                 ALSA (wm8960-soundcard)
                                             ↓
                                       Speakers 🔊
```

---

## Summary

✅ TTS system fully implemented with 12 emotion states
✅ Hardware configuration via ALSA
✅ Test script for verification
✅ Documentation complete

**Status**: Ready to use once ALSA configured on Pi!
