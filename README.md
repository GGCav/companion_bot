# Companion Bot

Companion Bot is a Raspberry Pi–based pet-style robot that talks, listens, reacts to touch, sees faces, and shows emotions on a small display. It runs a local pipeline (audio input → VAD → STT → LLM → TTS → display/sensors) with a memory system to keep context across interactions.

## Features
- Voice pipeline with WebRTC VAD, Whisper STT, and Ollama-backed LLM responses.
- Text-to-speech output plus pygame-driven expressive face renderer.
- Touch, proximity, and PIR sensors for physical interaction and awareness.
- SQLite-backed memory for user profiles and conversation history.
- Modular scripts for demos, hardware checks, and integration tests.

## Hardware & Software
- Raspberry Pi 4 recommended (audio card, mini mic, speaker, Pi Camera, touch sensors, ultrasonic/PIR sensors, optional servos).
- Python 3.11+ with system deps for audio (portaudio), camera (libcamera/OpenCV), and TTS/STT backends.
- Ollama installed with a small model (e.g., `llama3.2:3b`) for on-device LLM.

## Quick Start
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration
Edit `config/settings.yaml` to match your hardware (audio device indexes, sample rates, camera settings, sensor pins, servo pins). Ensure `config/asound.conf` matches your audio card if using ALSA, and copy it to `/etc/asound.conf` when running on the Pi.

## Running
- Full integration demo: `python scripts/demo_full_integration.py`
- Main entrypoint (service-style): `python main.py`
- Quick voice-only tests: see `scripts/test_voice_input.py` or `scripts/test_voice_llm.py`
- Expression display test: `scripts/test_emotion_display.py`

## Tests
Run a lightweight syntax check: `python -m compileall main.py src scripts`
Add or run pytest-based checks if you extend test coverage.

## Project Structure
- `main.py` — launches the full bot pipeline.
- `src/` — core modules for audio, llm, expression/display, sensors, vision, personality, and memory.
- `scripts/` — demos and hardware validation scripts.
- `config/` — runtime settings and audio config.
- `website/` — static project page assets.
- `flow_chart.png` — high-level system diagram.

## Notes
- Many scripts expect to run on a Pi with the listed peripherals; on other platforms, disable hardware-specific sections in `settings.yaml`.
- Keep models lightweight for real-time performance on the Pi.
