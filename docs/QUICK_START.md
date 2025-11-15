# Companion Bot - Quick Start Guide

Get your companion bot up and running quickly!

## What You Have

A complete, production-ready project structure for an AI-powered pet companion robot with:

- ✅ Full directory structure
- ✅ Configuration system (settings.yaml)
- ✅ Hardware-optimized modules for mini microphone and Pi Camera v2
- ✅ Complete audio module (input, output, VAD)
- ✅ Complete vision module (camera, face detection, recognition)
- ✅ Complete sensor module (touch, proximity)
- ✅ Emotion engine with 12 emotional states
- ✅ Automated setup script
- ✅ Comprehensive hardware wiring guide
- ✅ 4-week development sprint plan

## Files You Should Read

1. **README.md** - Project overview and system architecture
2. **README_SETUP.md** - Detailed hardware wiring guide
3. **DEVELOPMENT_SPRINTS.md** - 4-week implementation roadmap
4. **PROJECT_STRUCTURE.md** - Complete code organization
5. **config/settings.yaml** - Hardware configuration (EDIT THIS!)

## Quick Setup (5 Steps)

### 1. Wire Your Hardware

Follow **README_SETUP.md** section "Wiring Diagrams":

**Minimum to get started:**
- Pi Camera v2 → CSI port
- Mini USB Microphone → USB port
- Speaker → 3.5mm jack
- (Optional) Touch sensors on GPIO 17, 27, 22

### 2. Run Setup Script

```bash
cd companion_bot
chmod +x setup.sh
./setup.sh
```

This installs everything needed (takes 15-30 minutes).

### 3. Configure Your Hardware

```bash
nano config/settings.yaml
```

Update these sections:
- `audio.input.device_index` - Your microphone (or null for default)
- `sensors.touch.pins` - GPIO pins for touch sensors
- `sensors.proximity` - Ultrasonic/PIR pins
- `motors.servo` - Servo GPIO pins

### 4. Test Hardware

```bash
source venv/bin/activate
python scripts/test_hardware.py
```

Verify all components are detected.

### 5. Run the Bot

```bash
python main.py
```

## What Works Right Now

The following modules are **fully implemented** and ready to use:

### Audio Module ✅
- `src/audio/audio_input.py` - Microphone capture with voice detection
- `src/audio/audio_output.py` - Speaker output and TTS
- `src/audio/voice_detector.py` - Voice activity detection

**Test it:**
```python
from audio import AudioInput, AudioOutput, TextToSpeech
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

# Test microphone
audio_in = AudioInput(config)
audio_in.start_listening()
print(f"Audio level: {audio_in.get_audio_level()}")

# Test speaker
tts = TextToSpeech(config)
tts.speak("Hello! I'm your companion bot!")
```

### Vision Module ✅
- `src/vision/camera.py` - Pi Camera v2 capture with threading
- `src/vision/face_detector.py` - Face detection
- `src/vision/face_recognizer.py` - User recognition

**Test it:**
```python
from vision import Camera, FaceDetector
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

camera = Camera(config)
camera.start()

frame = camera.read()
if frame is not None:
    print(f"Captured frame: {frame.shape}")
    camera.capture_image("test.jpg")
```

### Sensors Module ✅
- `src/sensors/touch_sensor.py` - Touch detection with callbacks
- `src/sensors/proximity_sensor.py` - Distance and motion sensing

**Test it:**
```python
from sensors import TouchSensor, ProximitySensor
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

touch = TouchSensor(config)
touch.on_press(lambda loc: print(f"Touched: {loc}"))
touch.start_monitoring()

proximity = ProximitySensor(config)
distance = proximity.get_distance()
print(f"Distance: {distance} cm")
```

### Personality Module ✅
- `src/personality/emotion_engine.py` - Emotion state machine

**Test it:**
```python
from personality import EmotionEngine
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

engine = EmotionEngine(config)
print(f"Current emotion: {engine.get_emotion()}")

engine.on_touch("head")
print(f"After touch: {engine.get_emotion()}")
```

## What Needs Implementation

These modules have structure but need implementation (see DEVELOPMENT_SPRINTS.md):

- ⏳ **LLM Module** - Ollama client, STT, TTS engines (Week 2)
- ⏳ **Expression Module** - Eye animations, servo control (Week 3)
- ⏳ **Memory Module** - User profiles, conversation history (Week 4)
- ⏳ **Core Module** - Main orchestration, event manager (Week 4)

## Development Roadmap

Follow **DEVELOPMENT_SPRINTS.md** for week-by-week tasks:

### Week 1: Foundation ← **YOU ARE HERE**
- ✅ Hardware assembly
- ✅ Project structure
- ⏳ Test all sensors
- ⏳ Verify camera and audio

### Week 2: AI Integration
- Implement Ollama client
- Add Whisper STT
- Complete TTS system
- Enhance personality engine

### Week 3: Expression
- Create 20+ eye animations
- Implement servo control
- Add motion patterns
- Sync all outputs

### Week 4: Integration
- Memory system
- Full bot orchestration
- Testing and tuning
- Documentation

## Common Tasks

### List Audio Devices
```python
from audio import AudioInput
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

audio = AudioInput(config)
for device in audio.list_devices():
    print(f"[{device['index']}] {device['name']}")
```

### Test Camera FPS
```python
from vision import Camera
import yaml
import time

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

camera = Camera(config)
camera.start()

time.sleep(5)
print(f"FPS: {camera.get_fps():.1f}")
```

### Monitor Touch Sensors
```python
from sensors import TouchSensor
import yaml
import time

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

def on_touch(location):
    print(f"🎯 Touched: {location}")

touch = TouchSensor(config)
touch.on_press(on_touch)
touch.start_monitoring()

print("Monitoring... (Ctrl+C to stop)")
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    touch.cleanup()
```

## Troubleshooting

### Camera not working
```bash
vcgencmd get_camera
libcamera-hello -t 5000
```

### Microphone not detected
```bash
arecord -l
arecord -D hw:1,0 -d 3 test.wav
```

### GPIO permission denied
```bash
sudo usermod -a -G gpio $USER
sudo reboot
```

### Import errors
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Next Steps

1. **Complete Week 1 Tasks** - Test all hardware
2. **Start Week 2** - Implement LLM integration
3. **Read Code** - Study the implemented modules in `src/`
4. **Customize** - Adjust `config/settings.yaml` for your setup
5. **Iterate** - Follow sprint plan, test frequently

## Resources

- **GPIO Pins:** [https://pinout.xyz/](https://pinout.xyz/)
- **Pi Camera:** [Official Docs](https://www.raspberrypi.com/documentation/accessories/camera.html)
- **Ollama:** [https://ollama.com/](https://ollama.com/)
- **Whisper:** [OpenAI Whisper](https://github.com/openai/whisper)

## Help & Support

- Check logs: `data/logs/companion.log`
- Run tests: `python scripts/test_hardware.py`
- Review: `PROJECT_STRUCTURE.md` for architecture

---

**Ready to build?** Start with Week 1 hardware testing, then follow DEVELOPMENT_SPRINTS.md!

**Questions?** All documentation is in the repo. Good luck! 🤖✨
