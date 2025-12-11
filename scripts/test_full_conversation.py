#!/usr/bin/env python3
"""
Full Conversation Demo
Complete voice-to-voice conversation with LLM
Voice Input → Whisper STT → Ollama LLM → TTS → Speaker
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime


sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from llm import ConversationPipeline


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class FullConversationDemo:
    """Interactive full conversation demo with visual feedback"""

    def __init__(self, config: dict):
        """Initialize demo"""
        self.config = config
        self.pipeline = ConversationPipeline(config)
        self.conversation_log = []

    def start(self):
        """Start the demo"""
        self.print_header()


        if not self._check_prerequisites():
            return False


        self.pipeline.set_callbacks(
            on_listening=self.on_listening,
            on_transcribed=self.on_transcribed,
            on_thinking=self.on_thinking,
            on_responding=self.on_responding,
            on_speaking=self.on_speaking,
            on_complete=self.on_complete
        )


        print("\n🚀 Starting full conversation pipeline...\n")
        self.pipeline.start()

        self.print_instructions()

        return True

    def stop(self):
        """Stop the demo"""
        print("\n\n⏹️  Stopping conversation pipeline...")
        self.pipeline.stop()

        self.print_summary()

    def print_header(self):
        """Print demo header"""
        print("\n" + "=" * 80)
        print("🗣️  FULL CONVERSATION DEMO".center(80))
        print("Voice → Whisper STT → Ollama LLM → TTS → Speech".center(80))
        print("=" * 80)

    def _check_prerequisites(self) -> bool:
        """Check if all systems are ready"""
        print("\n📋 Checking prerequisites...")

        checks = []


        print("   🎤 Testing microphone...")
        mic_ok = self.pipeline.voice_input.test_microphone()
        checks.append(("Microphone", mic_ok))


        print("   🤖 Testing Ollama...")
        llm_ok = self.pipeline.conversation_manager.llm.is_available
        checks.append(("Ollama LLM", llm_ok))


        print("   🔊 Testing TTS...")
        try:
            self.pipeline.tts.speak("Test", wait=False)
            tts_ok = True
        except:
            tts_ok = False
        checks.append(("Text-to-Speech", tts_ok))


        print("\n   Results:")
        all_ok = True
        for name, ok in checks:
            status = "✅" if ok else "❌"
            print(f"      {status} {name}")
            if not ok:
                all_ok = False

        if not all_ok:
            print("\n   ❌ Some components failed - see troubleshooting below")
            self.print_troubleshooting()
            return False

        print("\n   ✅ All systems ready!")
        return True

    def print_instructions(self):
        """Print usage instructions"""
        print("┌" + "─" * 78 + "┐")
        print("│" + " HOW TO USE ".center(78) + "│")
        print("├" + "─" * 78 + "┤")
        print("│ 1. Speak naturally into your microphone                                   │")
        print("│ 2. Wait for the bot to detect speech end (automatic)                      │")
        print("│ 3. System will transcribe, think, and respond                             │")
        print("│ 4. Listen to the bot's voice response                                     │")
        print("│ 5. Continue the conversation!                                             │")
        print("│                                                                            │")
        print("│ Press Ctrl+C to stop and see statistics                                   │")
        print("└" + "─" * 78 + "┘")
        print("\n🎯 Ready! Start speaking...\n")

    def print_troubleshooting(self):
        """Print troubleshooting tips"""
        print("\n" + "=" * 80)
        print("🔧 TROUBLESHOOTING")
        print("=" * 80)

        print("\nMicrophone issues:")
        print("  • Check connection: arecord -l")
        print("  • Test recording: arecord -D hw:1,0 -d 3 test.wav && aplay test.wav")
        print("  • Adjust volume: alsamixer")

        print("\nOllama issues:")
        print("  • Start service: ollama serve")
        print(f"  • Pull model: ollama pull {self.config['llm']['ollama']['model']}")
        print("  • Check running: curl http://localhost:11434/api/tags")

        print("\nTTS issues:")
        print("  • Check speaker: aplay /usr/share/sounds/alsa/Front_Center.wav")
        print("  • Install espeak: sudo apt-get install espeak")

        print("=" * 80)

    def on_listening(self):
        """Called when user starts speaking"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] 🎤 LISTENING...")
        print("│")

    def on_transcribed(self, text: str):
        """Called when speech is transcribed"""
        print("│")
        print("└─ 📝 YOU SAID:")
        print(f"   \"{text}\"\n")

        self.conversation_log.append({
            'timestamp': datetime.now(),
            'role': 'user',
            'text': text
        })

    def on_thinking(self):
        """Called when LLM is processing"""
        print("   🤔 Thinking...")

    def on_responding(self, text: str, emotion: str):
        """Called when response is ready"""
        print(f"   🎭 Emotion: {emotion}")
        print(f"   💬 BOT SAYS:")
        print(f"   \"{text}\"")

        self.conversation_log.append({
            'timestamp': datetime.now(),
            'role': 'bot',
            'text': text,
            'emotion': emotion
        })

    def on_speaking(self):
        """Called when TTS starts"""
        print("   🔊 Speaking...\n")

    def on_complete(self):
        """Called when full cycle completes"""
        print("─" * 80)

    def print_summary(self):
        """Print session summary"""
        stats = self.pipeline.get_statistics()

        print("\n" + "=" * 80)
        print("📊 SESSION SUMMARY".center(80))
        print("=" * 80)

        print(f"\n💬 Conversation Statistics:")
        print(f"   Total conversations: {stats['conversations']}")
        print(f"   Avg response time: {stats['avg_response_time']:.2f}s")

        print(f"\n🎤 Voice Input:")
        voice_stats = stats['voice_input']
        print(f"   Total utterances: {voice_stats['total_utterances']}")
        print(f"   Avg transcription time: {voice_stats['avg_transcription_time']:.2f}s")

        print(f"\n🤖 LLM:")
        llm_stats = stats['llm']
        print(f"   Total requests: {llm_stats['total_requests']}")
        print(f"   Total tokens: {llm_stats['total_tokens']}")
        print(f"   Avg time: {llm_stats['avg_time_per_request']:.2f}s")

        print(f"\n🔊 TTS:")
        tts_stats = stats['tts']
        print(f"   Total utterances: {tts_stats['total_utterances']}")

        print(f"\n🎭 Current State:")
        conv_stats = stats['conversation']
        print(f"   Emotion: {conv_stats['current_emotion']}")
        print(f"   Messages: {conv_stats['message_count']}")


        if self.conversation_log:
            print(f"\n📜 Conversation Log:")
            for i, entry in enumerate(self.conversation_log, 1):
                time_str = entry['timestamp'].strftime("%H:%M:%S")
                role_icon = "👤" if entry['role'] == 'user' else "🤖"
                emotion_str = f" ({entry['emotion']})" if 'emotion' in entry else ""

                print(f"   [{time_str}] {role_icon} {entry['text'][:60]}{emotion_str}")

        print("\n" + "=" * 80)
        print("✅ Demo completed successfully!".center(80))
        print("=" * 80)

    def run(self):
        """Run the demo"""
        if not self.start():
            return 1

        try:

            while True:
                time.sleep(0.1)

        except KeyboardInterrupt:
            pass

        finally:
            self.stop()
            self.pipeline.cleanup()

        return 0


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("🤖 FULL CONVERSATION DEMO - Voice-to-Voice AI")
    print("=" * 80)


    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        print("❌ Config file not found!")
        print(f"   Looking for: {config_path}")
        return 1

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print("✅ Configuration loaded")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1


    demo = FullConversationDemo(config)
    return demo.run()


if __name__ == "__main__":
    sys.exit(main())
