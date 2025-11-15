# Companion Bot - 4 Week Development Sprints

## Project Overview
AI-powered pet companion robot with multimodal interaction (voice, touch, vision) featuring personality engine, emotional states, and expressive behaviors via TFT display and servo motors.

---

## Sprint 1: Foundation & Core Infrastructure (Week 1)

### Goals
Establish hardware foundation, configure Raspberry Pi environment, and implement basic sensor input systems.

### Tasks

#### Day 1-2: Hardware Setup & Environment Configuration
- [ ] Assemble Lab 3 Robot Kit base structure
- [ ] Install Raspberry Pi 4 and configure OS (Raspbian/Ubuntu)
- [ ] Set up development environment (Python 3.8+, git, virtual environment)
- [ ] Create project structure and repository
- [ ] Configure I2C, SPI, GPIO interfaces
- [ ] Test power management and battery systems

#### Day 3-4: Audio Input/Output System
- [ ] Connect and configure microphone array
- [ ] Test audio recording with `pyaudio` or `sounddevice`
- [ ] Implement audio buffer management
- [ ] Connect speaker and test audio playback
- [ ] Create audio preprocessing pipeline (noise reduction, normalization)
- [ ] Implement wake word detection (optional: using Porcupine)

#### Day 5-6: Touch & Proximity Sensors
- [ ] Wire capacitive touch sensors (head, body, back)
- [ ] Implement touch detection with debouncing logic
- [ ] Create touch event handler system
- [ ] Install PIR motion sensor
- [ ] Configure ultrasonic proximity sensors
- [ ] Test sensor polling vs. interrupt-based detection

#### Day 7: Camera & Vision Setup
- [ ] Connect Pi Camera module
- [ ] Install OpenCV and test camera capture
- [ ] Implement basic image preprocessing
- [ ] Test face detection with Haar Cascades or MediaPipe
- [ ] Create camera frame capture thread

### Deliverables
- Functional hardware assembly with all sensors connected
- Basic sensor reading scripts for each input modality
- Audio capture and playback working
- Camera capturing frames successfully
- Git repository with initial project structure

### Success Criteria
- All sensors return valid data
- Audio can be recorded and played back clearly
- Camera captures 30fps video
- No hardware conflicts or power issues

---

## Sprint 2: AI Core & Personality Engine (Week 2)

### Goals
Integrate LLM capabilities, implement speech processing, and build the emotion-based personality engine.

### Tasks

#### Day 8-9: Speech-to-Text Integration
- [ ] Choose STT solution (Google Speech API, Whisper, Vosk)
- [ ] Implement cloud-based STT (Google/Azure) OR
- [ ] Set up local Whisper model on Pi
- [ ] Create speech recognition pipeline
- [ ] Implement streaming audio to STT
- [ ] Test accuracy and latency benchmarks

#### Day 10-11: LLM Integration
- [ ] Set up cloud LLM API (OpenAI GPT-4 or Claude) OR
- [ ] Install Ollama and pull compact model (Llama 3.2, Phi-3)
- [ ] Implement LLM prompt templates for pet personality
- [ ] Create context management system
- [ ] Test response generation latency
- [ ] Implement fallback responses for offline mode

#### Day 12-13: Text-to-Speech & Voice Character
- [ ] Choose TTS solution (Google TTS, pyttsx3, Coqui TTS)
- [ ] Configure voice parameters (pitch, speed, tone) for pet character
- [ ] Create TTS queue system
- [ ] Test audio output quality
- [ ] Implement emotion-based voice modulation
- [ ] Cache common phrases for faster playback

#### Day 14: Personality Engine - Emotion State Machine
- [ ] Define emotion states: happy, curious, lonely, excited, sleepy, sad, playful
- [ ] Implement state machine with transition logic
- [ ] Create emotion scoring system based on inputs:
  - Voice tone/content → emotion mapping
  - Touch duration/frequency → affection scoring
  - Time alone → loneliness increase
  - Movement/activity → excitement level
- [ ] Implement emotion decay over time
- [ ] Create personality traits (shy, energetic, affectionate, curious)
- [ ] Test state transitions with simulated inputs

### Deliverables
- Working voice conversation pipeline (STT → LLM → TTS)
- Personality engine with 7+ emotion states
- State machine responding to multimodal inputs
- LLM generating contextual pet responses

### Success Criteria
- Speech recognition accuracy >80%
- LLM response time <3 seconds
- Smooth state transitions with logical behavior
- Voice output sounds natural and pet-like

---

## Sprint 3: Multimodal Expression & Output (Week 3)

### Goals
Implement visual expressions, physical movements, and cohesive emotion-to-output mapping.

### Tasks

#### Day 15-16: TFT Display & Eye Animation System
- [ ] Connect TFT display to Pi (SPI/HDMI)
- [ ] Install display libraries (pygame, Pillow, or TKinter)
- [ ] Design 20+ eye expressions:
  - Happy (wide eyes, sparkles)
  - Sad (droopy eyes, tears)
  - Excited (large pupils, bright)
  - Sleepy (half-closed, yawning)
  - Curious (wide, looking around)
  - Angry (narrowed, sharp)
  - Playful (winking, animated)
  - Confused (tilted, question marks)
  - Loving (heart-shaped pupils)
  - Scared (wide, shaking)
  - Bored (half-lidded, looking away)
  - Surprised (huge, eyebrows up)
  - And 8+ more variations
- [ ] Implement smooth animation transitions
- [ ] Create expression queue system
- [ ] Test animation frame rates (target 24-30fps)

#### Day 17-18: Servo Motor Control System
- [ ] Connect servo motors (head pan/tilt, ears, tail)
- [ ] Install servo control library (pigpio, RPi.GPIO, PCA9685)
- [ ] Calibrate servo ranges and limits
- [ ] Implement movement patterns:
  - Head: look left/right, up/down, tilt, shake, nod
  - Ears: perk up, droop, twitch
  - Tail: wag (fast/slow), curl, straight, droop
- [ ] Create smooth movement interpolation
- [ ] Implement concurrent motor control
- [ ] Add safety limits to prevent damage

#### Day 19-20: Emotion-to-Expression Mapping
- [ ] Create comprehensive emotion → output mapping:
  - `happy`: wide eyes + tail wag + upbeat voice
  - `excited`: sparkle eyes + rapid head movement + high-pitched voice
  - `curious`: wide eyes + head tilt + questioning tone
  - `sleepy`: droopy eyes + slow movements + quiet voice
  - `lonely`: sad eyes + droopy tail + soft whimper sounds
  - `playful`: winking + ear twitch + energetic tone
  - `scared`: wide eyes + ears back + hiding movements
- [ ] Implement multi-output coordinator (display + motors + audio sync)
- [ ] Add randomization to avoid repetitive behavior
- [ ] Create contextual behavior overlays (e.g., if touched while speaking)

#### Day 21: Integration with Robot Body Movement
- [ ] Integrate Lab 3 Robot Kit motor drivers
- [ ] Implement basic locomotion (forward, back, turn)
- [ ] Link body movement to personality states:
  - Excited → move forward toward user
  - Lonely → approach user slowly
  - Playful → circle movements
  - Scared → back away
- [ ] Add movement safety (edge detection, collision avoidance)

### Deliverables
- TFT display showing 20+ animated eye expressions
- Servo motors performing smooth, lifelike movements
- Synchronized multimodal outputs (eyes + motors + voice)
- Robot body responding to personality states

### Success Criteria
- Expressions change smoothly with <0.5s latency
- Motor movements are fluid and natural-looking
- All outputs coordinate without conflicts
- Robot expresses clear emotional states visually

---

## Sprint 4: Integration, Memory & Polish (Week 4)

### Goals
Implement long-term memory, integrate all systems, conduct testing, and refine user experience.

### Tasks

#### Day 22-23: Memory System Implementation
- [ ] Design memory database schema:
  - User profiles (name, voice signature, face encoding)
  - Interaction history (timestamps, topics, emotions)
  - Learned preferences (favorite activities, words, times)
  - Routines (daily patterns, typical interaction times)
- [ ] Choose storage (SQLite, JSON files, or Redis)
- [ ] Implement memory recording during interactions
- [ ] Create memory retrieval for LLM context
- [ ] Add face recognition memory (store/recall faces)
- [ ] Implement preference learning:
  - Track which interactions increase happiness
  - Remember user's name and personal details
  - Recall previous conversation topics
- [ ] Add memory decay for old/irrelevant data

#### Day 24: Full System Integration
- [ ] Create main control loop orchestrating all modules
- [ ] Implement concurrent thread management:
  - Camera thread (face detection)
  - Audio input thread (STT)
  - Touch sensor polling
  - Personality engine updates
  - Expression rendering
  - Motor control
  - Audio output (TTS)
- [ ] Add thread-safe communication (queues, locks)
- [ ] Implement priority system for competing behaviors
- [ ] Create graceful startup and shutdown sequences
- [ ] Add error handling and recovery mechanisms

#### Day 25: Advanced Personality Features
- [ ] Implement circadian rhythm (energy levels by time of day)
- [ ] Add mood persistence across sessions
- [ ] Create spontaneous behaviors (random movements, sounds)
- [ ] Implement attention-seeking when lonely
- [ ] Add reaction to environmental changes (light, sound, motion)
- [ ] Create idle animations (blinking, breathing, fidgeting)
- [ ] Tune emotion transition timings and thresholds

#### Day 26-27: Testing & Refinement
- [ ] Conduct unit tests for each module
- [ ] Integration testing with all sensors active
- [ ] User acceptance testing (3-5 testers)
- [ ] Measure and optimize performance:
  - CPU/memory usage
  - Response latency (target <2s for interactions)
  - Battery life duration
- [ ] Test edge cases:
  - No internet connection (offline mode)
  - Multiple users simultaneously
  - Rapid input changes
  - Long conversation sessions
- [ ] Fix identified bugs and issues
- [ ] Tune personality parameters based on feedback

#### Day 28: Documentation & Final Polish
- [ ] Create user manual/guide
- [ ] Document API and module interfaces
- [ ] Add code comments and docstrings
- [ ] Create demo video showcasing features
- [ ] Prepare project presentation materials
- [ ] Final calibration and parameter tuning
- [ ] Code cleanup and refactoring
- [ ] Create deployment checklist

### Deliverables
- Complete companion robot with all features integrated
- Memory system remembering users and preferences
- Comprehensive test results and bug fixes
- Documentation and user guide
- Demo video and presentation

### Success Criteria
- Robot successfully interacts with users across all modalities
- Memory recalls previous interactions accurately
- System runs stably for 30+ minute sessions
- Users report emotional connection with robot
- All features work cohesively without conflicts

---

## Technical Stack Summary

### Hardware
- Raspberry Pi 4 (4GB+ RAM recommended)
- Lab 3 Robot Kit body
- TFT display (3.5" or larger)
- Pi Camera Module v2 or v3
- USB microphone array or I2S microphone
- Speaker (3W or higher)
- 3-5 servo motors (SG90 or MG90S)
- Capacitive touch sensors (TTP223 or similar)
- PIR motion sensor
- Ultrasonic proximity sensors (HC-SR04)
- PCA9685 servo driver board (optional)
- Portable battery pack (10000mAh+)

### Software Stack
- **OS**: Raspberry Pi OS (Bookworm) or Ubuntu 22.04
- **Language**: Python 3.8+
- **LLM**: OpenAI API / Claude API / Ollama (Llama 3.2)
- **STT**: Whisper / Google Speech / Vosk
- **TTS**: Google TTS / Coqui TTS / pyttsx3
- **Vision**: OpenCV, MediaPipe
- **Display**: Pygame / Pillow
- **Audio**: pyaudio / sounddevice
- **GPIO**: RPi.GPIO / pigpio
- **Memory**: SQLite / JSON
- **Concurrency**: threading / asyncio

### Key Libraries
```
opencv-python
mediapipe
openai / anthropic
requests
pyaudio
pyttsx3 / gtts
pygame
pillow
RPi.GPIO
pigpio
sounddevice
whisper (openai-whisper)
sqlite3
numpy
```

---

## Risk Management

### Technical Risks
1. **LLM Latency**: Cloud APIs may have delays
   - *Mitigation*: Use local Ollama for faster response, implement loading animations

2. **Pi Performance**: Running AI models may be slow
   - *Mitigation*: Optimize with threading, use smaller models, cloud offloading

3. **Power Consumption**: Multiple motors and display drain battery
   - *Mitigation*: Implement sleep modes, use efficient power management

4. **Sensor Interference**: I2C/SPI conflicts
   - *Mitigation*: Careful pin planning, use multiplexers if needed

### Schedule Risks
1. **Component Delays**: Hardware may arrive late
   - *Mitigation*: Order components early, have backup suppliers

2. **Integration Complexity**: Combining systems may take longer
   - *Mitigation*: Allocate full week for integration, build modularly

---

## Success Metrics

### Functional Requirements
- [ ] Responds to voice commands within 3 seconds
- [ ] Recognizes and remembers at least 3 different users
- [ ] Displays 20+ distinct eye expressions
- [ ] Performs smooth motor movements without jittering
- [ ] Maintains conversation context for 10+ exchanges
- [ ] Operates continuously for 30+ minutes on battery

### User Experience Goals
- [ ] Users feel emotional connection to robot
- [ ] Robot personality feels consistent and believable
- [ ] Interactions feel natural and responsive
- [ ] Robot demonstrates learning over time
- [ ] Physical expressions match emotional states

### Technical Performance
- [ ] Main loop runs at 10+ Hz
- [ ] CPU usage <80% during active interaction
- [ ] Memory usage <2GB RAM
- [ ] Audio latency <500ms
- [ ] Display refresh rate 24+ fps

---

## Future Enhancements (Post-Sprint)

- Mobile app for remote interaction
- Cloud storage for shared memory across devices
- Advanced computer vision (object recognition, gesture control)
- Multiple personality modes (dog, cat, bird, etc.)
- Learning from interactions with reinforcement learning
- Integration with smart home devices
- Multi-robot social interactions
- Custom voice training for personalized sound
- AR/VR visualization of emotional states
- Behavior analytics dashboard

---

## References & Resources

- **Raspberry Pi Documentation**: https://www.raspberrypi.com/documentation/
- **OpenCV Tutorials**: https://docs.opencv.org/
- **OpenAI API**: https://platform.openai.com/docs
- **Ollama**: https://ollama.com/
- **Whisper**: https://github.com/openai/whisper
- **Pygame**: https://www.pygame.org/docs/
- **RPi.GPIO**: https://sourceforge.net/projects/raspberry-gpio-python/

---

**Last Updated**: November 10, 2025
**Project Duration**: 4 Weeks
**Team Size**: 1-4 developers
**Target Platform**: Raspberry Pi 4 (4GB RAM minimum)
