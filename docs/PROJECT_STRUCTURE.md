# Companion Bot - Project Structure

Complete overview of the project organization and module responsibilities.

## Directory Structure

```
companion_bot/
├── config/                      # Configuration files
│   └── settings.yaml           # Hardware & software configuration
│
├── src/                        # Source code modules
│   ├── audio/                  # Audio processing (mini microphone)
│   │   ├── __init__.py
│   │   ├── audio_input.py     # Microphone capture with VAD
│   │   ├── audio_output.py    # Speaker output and TTS
│   │   └── voice_detector.py  # Voice activity detection
│   │
│   ├── vision/                 # Computer vision (Pi Camera v2)
│   │   ├── __init__.py
│   │   ├── camera.py          # Camera capture with threading
│   │   ├── face_detector.py   # Face detection (MediaPipe/Haar)
│   │   └── face_recognizer.py # Face recognition & user identification
│   │
│   ├── sensors/                # Physical sensors
│   │   ├── __init__.py
│   │   ├── touch_sensor.py    # Capacitive touch sensors
│   │   └── proximity_sensor.py # Ultrasonic & PIR sensors
│   │
│   ├── personality/            # Emotion & behavior engine
│   │   ├── __init__.py
│   │   ├── emotion_engine.py  # Emotion state machine
│   │   └── behavior_controller.py # Behavior selection logic
│   │
│   ├── llm/                    # LLM integration
│   │   ├── __init__.py
│   │   ├── ollama_client.py   # Ollama API client
│   │   ├── stt_engine.py      # Speech-to-text (Whisper/Vosk)
│   │   └── tts_engine.py      # Text-to-speech
│   │
│   ├── expression/             # Output expressions
│   │   ├── __init__.py
│   │   ├── eye_animator.py    # TFT display animations
│   │   └── servo_controller.py # Servo motor control
│   │
│   ├── memory/                 # Long-term memory
│   │   ├── __init__.py
│   │   ├── user_memory.py     # User profiles & preferences
│   │   └── conversation_history.py # Conversation logs
│   │
│   └── core/                   # Main orchestration
│       ├── __init__.py
│       ├── companion_bot.py   # Main bot class
│       └── event_manager.py   # Event coordination
│
├── assets/                     # Media assets
│   ├── animations/            # Eye animation frames
│   └── sounds/                # Sound effects
│
├── data/                       # Runtime data (gitignored)
│   ├── users/                 # User profiles & face encodings
│   ├── conversations/         # Conversation history
│   └── logs/                  # Application logs
│
├── tests/                      # Unit tests
│   ├── test_audio.py
│   ├── test_vision.py
│   ├── test_sensors.py
│   └── test_personality.py
│
├── scripts/                    # Utility scripts
│   ├── test_hardware.py       # Hardware testing
│   ├── calibrate_servos.py    # Servo calibration
│   └── download_models.py     # Model download helper
│
├── docs/                       # Additional documentation
│
├── main.py                     # Main entry point
├── setup.sh                    # Installation script
├── requirements.txt            # Python dependencies
├── README.md                   # Project overview
├── README_SETUP.md            # Hardware setup guide
├── DEVELOPMENT_SPRINTS.md     # 4-week development plan
└── PROJECT_STRUCTURE.md       # This file
```

---

## Module Descriptions

### 1. Audio Module (`src/audio/`)

**Purpose:** Handle all audio input/output for mini microphone and speaker.

**Components:**
- **audio_input.py** - Captures audio from mini microphone
  - PyAudio stream management
  - Voice activity detection (VAD)
  - Automatic silence detection
  - Audio level monitoring
  - Recording start/stop with threading

- **audio_output.py** - Manages speaker output
  - Pygame mixer for sound effects
  - TTS integration (pyttsx3)
  - Async audio playback queue
  - Volume control

- **voice_detector.py** - Advanced voice detection
  - WebRTC VAD integration
  - Adaptive noise floor estimation
  - Hysteresis-based detection
  - Confidence scoring

**Key Features:**
- Optimized for mini microphones (mono, 16kHz)
- Low-latency audio processing
- Robust noise handling
- Threaded architecture for non-blocking operation

---

### 2. Vision Module (`src/vision/`)

**Purpose:** Process Pi Camera v2 input for face detection and recognition.

**Components:**
- **camera.py** - Pi Camera v2 handler
  - Supports picamera2 (preferred) and OpenCV fallback
  - Threaded frame capture
  - Configurable resolution and FPS
  - Frame buffering and rotation
  - FPS monitoring

- **face_detector.py** - Face detection
  - MediaPipe face detection (primary)
  - Haar Cascade fallback
  - Bounding box extraction
  - Confidence thresholding

- **face_recognizer.py** - User identification
  - face_recognition library (dlib)
  - Face encoding storage
  - User profile management
  - Recognition confidence scoring
  - Persistent storage (pickle)

**Key Features:**
- Optimized for Pi Camera v2 (640x480@30fps default)
- Graceful degradation (MediaPipe → Haar)
- Face encoding caching
- Multi-user support

---

### 3. Sensors Module (`src/sensors/`)

**Purpose:** Interface with physical sensors for touch and proximity.

**Components:**
- **touch_sensor.py** - Capacitive touch handling
  - Multi-sensor support (head, body, back)
  - Debouncing logic
  - Long-press detection
  - Event callbacks (press, release, long_press)
  - Threaded monitoring

- **proximity_sensor.py** - Distance and motion sensing
  - Ultrasonic sensor (HC-SR04)
  - PIR motion detection
  - Distance measurement (cm)
  - Threshold-based detection

**Key Features:**
- Event-driven architecture
- Configurable polling rates
- GPIO cleanup on shutdown
- Debouncing and filtering

---

### 4. Personality Module (`src/personality/`)

**Purpose:** Implement emotion-based behavior and personality.

**Components:**
- **emotion_engine.py** - Emotion state machine
  - 12 emotional states (happy, sad, excited, curious, etc.)
  - Multi-emotion scoring system
  - State transitions with decay
  - Personality traits (energy, sociability, curiosity, affection)
  - Circadian rhythm (time-of-day effects)
  - Event handlers (touch, voice, face recognition)

- **behavior_controller.py** - Behavior selection *[To be implemented]*
  - Maps emotions to behaviors
  - Action prioritization
  - Context-aware responses
  - Randomization for variety

**Key Features:**
- Dynamic emotional states
- Time-based decay and loneliness
- Multi-modal input integration
- Personality trait modifiers

---

### 5. LLM Module (`src/llm/`)

**Purpose:** Integrate language models and speech processing.

**Components:**
- **ollama_client.py** - Ollama API integration *[To be implemented]*
  - Local LLM inference (qwen2.5:0.5b)
  - Personality prompt templates
  - Context management
  - Timeout handling
  - Fallback responses

- **stt_engine.py** - Speech-to-text *[To be implemented]*
  - Whisper model integration (base)
  - Google Speech API fallback
  - Vosk offline support
  - Language detection

- **tts_engine.py** - Text-to-speech *[To be implemented]*
  - pyttsx3 for offline TTS
  - Google TTS (gTTS) for quality
  - Voice modulation (pitch, speed)
  - Emotion-based voice changes

**Key Features:**
- Local-first approach (works offline)
- Cloud API fallbacks
- Pet-like personality prompts
- Short response generation

---

### 6. Expression Module (`src/expression/`)

**Purpose:** Control visual and physical expressions.

**Components:**
- **eye_animator.py** - TFT display animations *[To be implemented]*
  - 20+ eye expressions
  - Smooth frame transitions
  - Pygame rendering
  - Idle animations (blinking, looking)
  - Emotion-to-expression mapping

- **servo_controller.py** - Motor control *[To be implemented]*
  - 5-servo coordination
  - Smooth movement interpolation
  - Head pan/tilt
  - Ear and tail movements
  - Safety limits
  - PCA9685 support

**Key Features:**
- Synchronized multimodal output
- Emotion-driven expressions
- Natural movement patterns
- Randomization for liveliness

---

### 7. Memory Module (`src/memory/`)

**Purpose:** Store and recall user information and interactions.

**Components:**
- **user_memory.py** - User profiles *[To be implemented]*
  - SQLite database
  - Face encoding associations
  - Preference tracking
  - Interaction statistics

- **conversation_history.py** - Conversation logs *[To be implemented]*
  - Message history
  - Context windows for LLM
  - Timestamp tracking
  - Topic extraction

**Key Features:**
- Persistent storage
- Multi-user support
- Privacy-aware (local only)
- Automatic cleanup

---

### 8. Core Module (`src/core/`)

**Purpose:** Orchestrate all modules and manage main control loop.

**Components:**
- **companion_bot.py** - Main bot class *[To be implemented]*
  - Module initialization
  - Main update loop
  - Thread coordination
  - Graceful shutdown
  - Error handling

- **event_manager.py** - Event coordination *[To be implemented]*
  - Cross-module events
  - Priority queue
  - Event dispatching
  - Conflict resolution

**Key Features:**
- Centralized control
- Thread-safe operations
- Performance monitoring
- Modular architecture

---

## Configuration System

### settings.yaml Structure

The configuration file uses YAML format for easy editing:

```yaml
audio:
  input: {...}    # Microphone settings
  output: {...}   # Speaker settings
  processing: {...} # VAD, noise reduction

vision:
  camera: {...}   # Pi Camera v2 resolution, FPS
  processing: {...} # Face detection settings
  face: {...}     # Recognition thresholds

sensors:
  touch: {...}    # GPIO pins, debounce
  proximity: {...} # Ultrasonic, PIR settings

motors:
  servo: {...}    # Servo pins, ranges
  movement: {...} # Robot motors

display:
  {...}           # TFT display settings

personality:
  emotions: [...]  # Available emotions
  traits: {...}    # Personality parameters
  dynamics: {...}  # Emotion transitions

llm:
  ollama: {...}   # Model, URL
  generation: {...} # Temperature, tokens

speech:
  stt: {...}      # STT provider, model
  tts: {...}      # TTS provider, voice

memory:
  {...}           # Database, cleanup

system:
  {...}           # Logging, performance
```

All settings are centralized and can be adjusted without code changes.

---

## Data Flow

### Input Flow
```
Microphone → AudioInput → VAD → STT → LLM
Camera → FaceDetector → FaceRecognizer → PersonalityEngine
TouchSensor → EventManager → PersonalityEngine
ProximitySensor → EventManager → PersonalityEngine
```

### Processing Flow
```
PersonalityEngine ← All Inputs
    ↓
EmotionState Updates
    ↓
BehaviorController
    ↓
Action Selection
```

### Output Flow
```
LLM → TTS → Speaker
EmotionState → EyeAnimator → TFT Display
EmotionState → ServoController → Physical Movement
Memory → All Modules (context)
```

---

## Development Workflow

### Phase 1: Foundation (Week 1)
- ✅ Hardware setup
- ✅ Module structure
- ✅ Configuration system
- ⏳ Hardware testing

### Phase 2: AI Integration (Week 2)
- ⏳ LLM integration
- ⏳ STT/TTS implementation
- ⏳ Personality engine completion

### Phase 3: Expression (Week 3)
- ⏳ Eye animations
- ⏳ Servo control
- ⏳ Multimodal coordination

### Phase 4: Integration (Week 4)
- ⏳ Full system integration
- ⏳ Memory system
- ⏳ Testing and tuning

---

## Key Technologies

- **Language:** Python 3.8+
- **Hardware Interface:** RPi.GPIO, pigpio
- **Computer Vision:** OpenCV, MediaPipe, face_recognition
- **Audio:** PyAudio, WebRTC VAD, pyttsx3
- **LLM:** Ollama (qwen2.5:0.5b)
- **STT:** Whisper (base model)
- **Display:** Pygame
- **Database:** SQLite
- **Concurrency:** threading, asyncio

---

## Getting Started

1. **Hardware Setup:**
   ```bash
   # Follow README_SETUP.md for wiring
   ```

2. **Software Installation:**
   ```bash
   ./setup.sh
   ```

3. **Configuration:**
   ```bash
   nano config/settings.yaml
   # Adjust GPIO pins and hardware settings
   ```

4. **Testing:**
   ```bash
   source venv/bin/activate
   python scripts/test_hardware.py
   ```

5. **Run:**
   ```bash
   python main.py
   ```

---

## Module Status Legend

- ✅ **Complete** - Fully implemented and tested
- ⏳ **In Progress** - Stub/partial implementation
- 📝 **Planned** - Not yet started

### Current Status

| Module | Status | Notes |
|--------|--------|-------|
| Audio Input | ✅ | Full implementation with VAD |
| Audio Output | ✅ | TTS and sound playback |
| Camera | ✅ | Pi Camera v2 support |
| Face Detection | ✅ | MediaPipe + Haar |
| Face Recognition | ✅ | User identification |
| Touch Sensors | ✅ | Multi-sensor with events |
| Proximity Sensors | ✅ | Ultrasonic + PIR |
| Emotion Engine | ✅ | State machine complete |
| Behavior Controller | 📝 | Planned |
| Ollama Client | 📝 | Planned |
| STT Engine | 📝 | Planned |
| TTS Engine | 📝 | Planned |
| Eye Animator | 📝 | Planned |
| Servo Controller | 📝 | Planned |
| User Memory | 📝 | Planned |
| Conversation History | 📝 | Planned |
| CompanionBot Core | 📝 | Planned |
| Event Manager | 📝 | Planned |

---

## Contributing

When adding new modules or features:

1. Follow existing code structure
2. Add comprehensive docstrings
3. Include test cases in `tests/`
4. Update this document
5. Log appropriately
6. Handle cleanup in `cleanup()` methods

---

## License

[Your License Here]

---

**Project:** ECE 5725 - Companion Bot
**Hardware:** Raspberry Pi 4, Mini Microphone, Pi Camera v2
**Last Updated:** November 2025
