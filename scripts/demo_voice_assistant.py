#!/usr/bin/env python3
"""
Voice Assistant Demo
Complete demo of voice input with mini microphone and Whisper
Shows real-time transcription with visual feedback
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from llm.voice_pipeline import VoicePipeline

# Configure logging (DEBUG level to match working test script)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class VoiceAssistantDemo:
    """Interactive voice assistant demo"""

    def __init__(self, config: dict):
        """Initialize demo"""
        self.config = config
        self.pipeline = VoicePipeline(config)
        self.is_running = False
        self.conversation_history = []

    def start(self):
        """Start the demo"""
        self.print_header()

        # Test microphone
        print("\n🎙️  Testing microphone...")
        if not self.pipeline.test_microphone():
            print("❌ Microphone test failed!")
            self.print_troubleshooting()
            return False

        print("✅ Microphone is working!\n")

        # Set up callbacks
        self.pipeline.set_transcription_callback(self.on_transcription)
        self.pipeline.set_speech_callbacks(self.on_speech_start, self.on_speech_end)

        # Start pipeline
        print("🚀 Starting voice assistant...\n")
        self.pipeline.start()
        self.is_running = True

        self.print_instructions()

        return True

    def stop(self):
        """Stop the demo"""
        if not self.is_running:
            return

        print("\n\n⏹️  Stopping voice assistant...")
        self.is_running = False
        self.pipeline.cleanup()

        self.print_summary()

    def print_header(self):
        """Print demo header"""
        print("\n" + "=" * 80)
        print("🤖 VOICE ASSISTANT DEMO".center(80))
        print("Mini Microphone + OpenAI Whisper".center(80))
        print("=" * 80)

    def print_instructions(self):
        """Print usage instructions"""
        print("┌" + "─" * 78 + "┐")
        print("│" + " INSTRUCTIONS ".center(78) + "│")
        print("├" + "─" * 78 + "┤")
        print("│ 1. Speak clearly into your mini microphone                                │")
        print("│ 2. The system will automatically detect when you start/stop speaking      │")
        print("│ 3. Wait for transcription results                                         │")
        print("│ 4. Try different commands and questions                                   │")
        print("│ 5. Press Ctrl+C to stop and see statistics                                │")
        print("└" + "─" * 78 + "┘")
        print("\n🎯 Ready! Start speaking...\n")

    def print_troubleshooting(self):
        """Print troubleshooting tips"""
        print("\n" + "=" * 80)
        print("Troubleshooting Tips:")
        print("=" * 80)
        print("1. Check microphone connection:")
        print("   arecord -l")
        print("\n2. Test recording:")
        print("   arecord -D hw:1,0 -d 3 test.wav && aplay test.wav")
        print("\n3. Adjust volume:")
        print("   alsamixer")
        print("\n4. Check config:")
        print("   config/settings.yaml")
        print("=" * 80)

    def on_speech_start(self):
        """Called when speech is detected"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] 🎤 LISTENING...")
        print("│")

    def on_speech_end(self):
        """Called when speech ends"""
        print("│")
        print("└─ ⏳ Processing with Whisper...")

    def on_transcription(self, result: dict):
        """Called when transcription is complete"""
        text = result['text']
        confidence = result['confidence']
        language = result['language']
        duration = result['duration']

        # Add to history
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'text': text,
            'confidence': confidence,
            'language': language,
            'duration': duration
        })

        # Print result with visual formatting
        self.print_transcription_result(result)

        # Simulate response (placeholder for actual LLM integration)
        self.simulate_response(text)

    def print_transcription_result(self, result: dict):
        """Print formatted transcription result"""
        text = result['text']
        confidence = result['confidence']
        language = result['language']
        duration = result['duration']

        # Confidence indicator
        if confidence >= 0.8:
            conf_emoji = "✅"
            conf_level = "HIGH"
        elif confidence >= 0.5:
            conf_emoji = "⚠️"
            conf_level = "MEDIUM"
        else:
            conf_emoji = "❌"
            conf_level = "LOW"

        # Print formatted output
        print("\n┌" + "─" * 78 + "┐")
        print(f"│ 💬 YOU SAID:" + " " * 63 + "│")
        print(f"│    \"{text}\"" + " " * (73 - len(text)) + "│")
        print("├" + "─" * 78 + "┤")
        print(f"│ {conf_emoji} Confidence: {conf_level} ({confidence:.0%})  "
              f"│  🌍 Language: {language.upper()}  "
              f"│  ⏱️  {duration:.2f}s" + " " * (26 - len(f"{duration:.2f}s")) + "│")
        print("└" + "─" * 78 + "┘")

    def simulate_response(self, text: str):
        """Simulate assistant response (placeholder)"""
        text_lower = text.lower()

        # Simple keyword-based responses
        responses = {
            'hello': "Hello! How can I help you today?",
            'hi': "Hi there! Nice to hear from you!",
            'how are you': "I'm doing great! Thanks for asking. How are you?",
            'thank': "You're welcome!",
            'bye': "Goodbye! Have a great day!",
            'name': "I'm your companion bot, powered by Whisper voice recognition!",
            'weather': "I don't have weather data yet, but that's a planned feature!",
            'time': f"The current time is {datetime.now().strftime('%I:%M %p')}",
        }

        response = None
        for keyword, reply in responses.items():
            if keyword in text_lower:
                response = reply
                break

        if not response:
            response = "I heard you! (LLM integration coming soon to generate smart responses)"

        # Print bot response
        print("┌" + "─" * 78 + "┐")
        print(f"│ 🤖 BOT:" + " " * 68 + "│")
        print(f"│    {response}" + " " * (74 - len(response)) + "│")
        print("└" + "─" * 78 + "┘")
        print()

    def print_summary(self):
        """Print session summary"""
        stats = self.pipeline.get_statistics()

        print("\n" + "=" * 80)
        print("📊 SESSION SUMMARY".center(80))
        print("=" * 80)

        print(f"\n📈 Statistics:")
        print(f"   Total Utterances:         {stats['total_utterances']}")
        print(f"   Total Transcription Time: {stats['total_transcription_time']:.2f}s")
        print(f"   Avg Time per Utterance:   {stats['avg_transcription_time']:.2f}s")

        if self.conversation_history:
            print(f"\n💬 Conversation History:")
            for i, entry in enumerate(self.conversation_history, 1):
                time_str = entry['timestamp'].strftime("%H:%M:%S")
                print(f"   [{time_str}] #{i}: \"{entry['text']}\" "
                      f"(conf: {entry['confidence']:.0%})")

            # Calculate average confidence
            avg_conf = sum(e['confidence'] for e in self.conversation_history) / len(self.conversation_history)
            print(f"\n   Average Confidence: {avg_conf:.0%}")

        # Whisper model info
        stt_stats = stats.get('stt_stats', {})
        print(f"\n🤖 Whisper Model:")
        print(f"   Model Size: {stt_stats.get('model_size', 'N/A')}")
        print(f"   Device: {stt_stats.get('device', 'N/A')}")

        print("\n" + "=" * 80)
        print("✅ Demo completed successfully!".center(80))
        print("=" * 80 + "\n")

    def run(self):
        """Run the demo"""
        if not self.start():
            return 1

        try:
            # Keep running until interrupted
            while self.is_running:
                time.sleep(0.1)

        except KeyboardInterrupt:
            pass

        finally:
            self.stop()

        return 0


def main():
    """Main entry point"""
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        print("❌ Config file not found!")
        print(f"Looking for: {config_path}")
        print("\nPlease run setup.sh first or create config/settings.yaml")
        return 1

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1

    # Create and run demo
    demo = VoiceAssistantDemo(config)
    return demo.run()


if __name__ == "__main__":
    sys.exit(main())
