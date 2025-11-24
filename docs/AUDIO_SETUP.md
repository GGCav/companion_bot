# Audio Setup Guide - wm8960-soundcard

Complete guide for configuring the wm8960-soundcard on Raspberry Pi for the companion bot's TTS (Text-to-Speech) output.

---

## Hardware Overview

**Sound Card**: wm8960-soundcard
**ALSA Path**: `hw:0,0` (card 0, device 0)
**Device**: `bcm2835-i2s-wm8960-hifi wm8960-hifi-0`

**Connection**:
- Connect speakers or headphones to the wm8960-soundcard audio jack
- Ensure the sound card is properly seated on the Raspberry Pi GPIO pins
- Power on the Raspberry Pi

---

## 1. Verify Hardware Detection

First, verify that the Raspberry Pi detects the wm8960-soundcard:

```bash
# List all playback devices
aplay -l
```

**Expected Output**:
```
**** List of PLAYBACK Hardware Devices ****
card 0: wm8960soundcard [wm8960-soundcard], device 0: bcm2835-i2s-wm8960-hifi wm8960-hifi-0 [bcm2835-i2s-wm8960-hifi wm8960-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

If you don't see this, check:
- Sound card physical connection
- `/boot/config.txt` has wm8960 overlay enabled
- Kernel modules loaded: `lsmod | grep snd`

---

## 2. Install ALSA Configuration

The companion bot includes a pre-configured ALSA file that sets wm8960-soundcard as the default audio device.

### Step 1: Copy Configuration

```bash
# Copy ALSA config to system
sudo cp ~/companion_bot/config/asound.conf /etc/asound.conf
```

### Step 2: Verify Configuration

```bash
# Display the configuration
cat /etc/asound.conf
```

You should see the wm8960-soundcard configuration with card 0, device 0.

### Step 3: Reboot (Recommended)

```bash
sudo reboot
```

After reboot, the wm8960-soundcard will be the system's default audio device.

---

## 3. Test Audio Output

### Test with ALSA

```bash
# Play test tone through default device (should use wm8960)
speaker-test -c 2 -t wav

# Press Ctrl+C to stop
```

You should hear a test tone from the speakers connected to wm8960-soundcard.

### Test with aplay

```bash
# Play a WAV file (if you have one)
aplay /usr/share/sounds/alsa/Front_Center.wav
```

---

## 4. Test TTS Engine

The companion bot includes a comprehensive TTS hardware test script.

### Run TTS Test

```bash
cd ~/companion_bot
python scripts/test_tts_hardware.py
```

**What it tests**:
1. ✅ Audio device information
2. ✅ TTS engine initialization
3. ✅ All 12 emotion voices (happy, sad, excited, etc.)
4. ✅ Multi-emotion speech with transitions
5. ✅ Performance statistics

**Expected Behavior**:
- You should hear spoken phrases through the wm8960-soundcard
- Each emotion should have different voice characteristics (speed, pitch, volume)
- No audio errors in the output

---

## 5. Volume Control

### Check Current Volume

```bash
# Open ALSA mixer
alsamixer
```

- Press **F6** to select sound card (choose wm8960-soundcard)
- Adjust volume with arrow keys
- Press **Esc** to exit

### Set Volume from Command Line

```bash
# Set volume to 80%
amixer -c 0 set Speaker 80%

# Unmute if muted
amixer -c 0 set Speaker unmute
```

### Persistent Volume Settings

```bash
# Save current volume settings
sudo alsactl store
```

---

## 6. Configuration in settings.yaml

The companion bot's TTS configuration is in `config/settings.yaml`:

```yaml
audio:
  output:
    device_index: null  # null = system default (wm8960-soundcard via /etc/asound.conf)
    sample_rate: 22050
    channels: 1

speech:
  tts:
    provider: "pyttsx3"  # Offline TTS engine
    pyttsx3:
      rate: 150         # Words per minute
      volume: 0.9       # 0.0 to 1.0
      voice_id: 0       # Voice index
      pitch: 1.5        # Higher pitch for cute pet voice
```

**Key Points**:
- `device_index: null` uses the system default (configured via `/etc/asound.conf`)
- Volume in settings.yaml is software volume (0.0-1.0)
- Hardware volume controlled via `alsamixer` or `amixer`

---

## 7. Troubleshooting

### Problem: No Audio Output

**Check 1: Hardware Connection**
```bash
aplay -l  # Should show wm8960-soundcard
```

**Check 2: Default Device**
```bash
cat /etc/asound.conf  # Should have wm8960 config
```

**Check 3: Volume Level**
```bash
alsamixer  # Check if muted or volume too low
```

**Check 4: Test Directly**
```bash
speaker-test -D hw:0,0 -c 2 -t wav  # Explicit device test
```

### Problem: Garbled or Distorted Audio

**Solution 1: Adjust Sample Rate**

Edit `/etc/asound.conf` and change the dmix rate:
```
slave {
    pcm "hw:0,0"
    rate 44100  # Try 44100 instead of 48000
}
```

**Solution 2: Buffer Size**

Increase buffer size in `/etc/asound.conf`:
```
slave {
    period_size 2048
    buffer_size 8192
}
```

### Problem: "Device or resource busy"

**Solution**: Another process is using the audio device

```bash
# Find processes using audio
sudo lsof /dev/snd/*

# Kill specific process (if needed)
sudo kill <PID>
```

### Problem: pyttsx3 Errors

**Check espeak Installation**:
```bash
# pyttsx3 uses espeak on Linux
which espeak
# or
which espeak-ng

# Install if missing
sudo apt install espeak espeak-ng
```

---

## 8. Advanced: Software Mixing (Multiple Apps)

If you want multiple applications to use audio simultaneously, enable dmix in `/etc/asound.conf`.

The config file includes commented-out dmix configuration. To enable:

1. Edit `/etc/asound.conf`:
```bash
sudo nano /etc/asound.conf
```

2. Uncomment the dmix section at the bottom:
```
pcm.!default {
    type plug
    slave.pcm "dmixed"
}
```

3. Restart ALSA:
```bash
sudo /etc/init.d/alsa-utils restart
```

---

## 9. TTS System Architecture

```
Conversation Flow:
  User speaks
    ↓
  Voice Pipeline (Whisper STT)
    ↓
  LLM Processing (Ollama)
    ↓ (generates response + emotion)
  ConversationManager
    ↓
  TTSEngine.speak_with_emotion()
    ↓ (applies emotion modulation)
  TextToSpeech (pyttsx3)
    ↓ (espeak synthesis)
  ALSA (system default = wm8960)
    ↓
  wm8960-soundcard
    ↓
  Speakers 🔊
```

---

## 10. Emotion Voice Characteristics

The TTS engine modulates voice parameters based on emotion:

| Emotion | Speed | Pitch | Volume | Description |
|---------|-------|-------|--------|-------------|
| **happy** | 1.1x | 1.2x | 1.0x | Upbeat and cheerful |
| **excited** | 1.3x | 1.4x | 1.1x | Fast and high-pitched |
| **sad** | 0.8x | 0.8x | 0.9x | Slow and low |
| **sleepy** | 0.7x | 0.7x | 0.8x | Very slow and quiet |
| **angry** | 1.2x | 0.9x | 1.0x | Fast but lower pitch |
| **scared** | 1.1x | 1.3x | 0.9x | Fast and high, quieter |
| **loving** | 0.9x | 1.1x | 0.95x | Gentle and warm |
| **playful** | 1.15x | 1.25x | 1.05x | Bouncy and fun |
| **curious** | 1.05x | 1.15x | 1.0x | Slightly upbeat |
| **lonely** | 0.85x | 0.9x | 0.85x | Slow and quiet |
| **bored** | 0.8x | 0.85x | 0.9x | Monotone and slow |
| **surprised** | 1.25x | 1.35x | 1.05x | Fast and high |

*Speed: speech rate multiplier*
*Pitch: pitch multiplier (note: limited support in pyttsx3)*
*Volume: volume multiplier*

---

## 11. Testing Checklist

Before deploying the companion bot, verify:

- [ ] wm8960-soundcard detected (`aplay -l`)
- [ ] `/etc/asound.conf` configured
- [ ] Audio test passes (`speaker-test`)
- [ ] Volume adjusted (`alsamixer`)
- [ ] TTS test passes (`python scripts/test_tts_hardware.py`)
- [ ] All 12 emotion voices work
- [ ] Multi-emotion speech works
- [ ] No audio glitches or distortion
- [ ] Volume levels appropriate for environment

---

## 12. Quick Reference Commands

```bash
# Device Info
aplay -l                          # List playback devices
cat /etc/asound.conf              # Show ALSA config

# Audio Testing
speaker-test -c 2 -t wav          # Test tone
aplay <file.wav>                  # Play WAV file

# Volume Control
alsamixer                         # Interactive mixer
amixer -c 0 set Speaker 80%       # Set volume 80%
sudo alsactl store                # Save volume settings

# TTS Testing
cd ~/companion_bot
python scripts/test_tts_hardware.py

# Troubleshooting
sudo lsof /dev/snd/*              # Check audio device usage
lsmod | grep snd                  # Check sound modules
dmesg | grep wm8960               # Check kernel messages
```

---

## Summary

✅ **Hardware**: wm8960-soundcard (card 0, device 0)
✅ **Configuration**: `/etc/asound.conf` sets default device
✅ **TTS Engine**: pyttsx3 with espeak backend
✅ **Emotions**: 12 emotion states with voice modulation
✅ **Testing**: `scripts/test_tts_hardware.py`
✅ **Volume**: Control via `alsamixer` or `amixer`

The TTS pipeline is fully implemented and ready to use once the ALSA configuration is deployed to the Raspberry Pi!

---

**Created**: November 2025
**Status**: ✅ Production Ready
**Hardware**: Raspberry Pi + wm8960-soundcard
**Software**: pyttsx3, espeak, ALSA
