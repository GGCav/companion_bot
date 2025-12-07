#!/usr/bin/env python3
"""
Full System Integration Test
Tests all components (STT, LLM, TTS, Expression, Memory) with latency monitoring
"""

import sys
import time
import json
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from colorama import init, Fore, Style
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback: no colors
    class Fore:
        CYAN = GREEN = YELLOW = RED = ''
    class Style:
        RESET_ALL = ''

import yaml

# Component imports
from llm.ollama_client import OllamaClient
from llm.conversation_manager import ConversationManager
from llm.tts_engine import TTSEngine
from llm.stt_engine import STTEngine
from expression import EmotionDisplay
from memory import initialize_memory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class LatencyMonitor:
    """
    Monitors and tracks latency metrics for all components
    """
    def __init__(self):
        self.metrics = defaultdict(list)
        self.current_timers = {}

    def start_timer(self, metric_name: str):
        """Start timing a metric"""
        self.current_timers[metric_name] = time.time()

    def end_timer(self, metric_name: str) -> float:
        """
        End timing and record duration

        Returns:
            Duration in seconds
        """
        if metric_name not in self.current_timers:
            logger.warning(f"Timer '{metric_name}' was not started")
            return 0.0

        start_time = self.current_timers[metric_name]
        duration = time.time() - start_time
        self.metrics[metric_name].append(duration)
        del self.current_timers[metric_name]
        return duration

    def record_metric(self, metric_name: str, value: float):
        """Directly record a metric value"""
        self.metrics[metric_name].append(value)

    def get_statistics(self) -> dict:
        """
        Calculate statistics for all metrics

        Returns:
            Dict with min, max, avg, p95 for each metric
        """
        stats = {}

        for metric_name, values in self.metrics.items():
            if not values:
                continue

            values_array = np.array(values)
            stats[metric_name] = {
                'min': float(np.min(values_array)),
                'max': float(np.max(values_array)),
                'avg': float(np.mean(values_array)),
                'p95': float(np.percentile(values_array, 95)),
                'count': len(values),
                'total': float(np.sum(values_array))
            }

        return stats

    def print_summary(self):
        """Print colorized latency summary to terminal"""
        stats = self.get_statistics()

        if not stats:
            print(f"{Fore.YELLOW}No metrics recorded yet{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 LATENCY STATISTICS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

        # End-to-end
        if 'end_to_end_latency' in stats:
            e2e = stats['end_to_end_latency']
            print(f"{Fore.GREEN}End-to-End Latency:{Style.RESET_ALL}")
            print(f"  Average: {e2e['avg']:.3f}s")
            print(f"  Min: {e2e['min']:.3f}s | Max: {e2e['max']:.3f}s | "
                  f"P95: {e2e['p95']:.3f}s | Count: {e2e['count']}\n")

        # Perceived latency
        if 'perceived_latency' in stats:
            perc = stats['perceived_latency']
            print(f"{Fore.GREEN}Perceived Latency (to first audio):{Style.RESET_ALL}")
            print(f"  Average: {perc['avg']:.3f}s")
            print(f"  Min: {perc['min']:.3f}s | Max: {perc['max']:.3f}s | "
                  f"P95: {perc['p95']:.3f}s\n")

        # STT metrics (if voice mode used)
        if 'stt_total' in stats:
            stt = stats['stt_total']
            print(f"{Fore.GREEN}STT Latency:{Style.RESET_ALL}")
            print(f"  Average: {stt['avg']:.3f}s")
            print(f"  Min: {stt['min']:.3f}s | Max: {stt['max']:.3f}s | "
                  f"P95: {stt['p95']:.3f}s\n")

        if 'stt_confidence' in stats:
            conf = stats['stt_confidence']
            print(f"{Fore.GREEN}STT Confidence:{Style.RESET_ALL}")
            print(f"  Average: {conf['avg']:.2f}")
            print(f"  Min: {conf['min']:.2f} | Max: {conf['max']:.2f}\n")

        # Component breakdown
        print(f"{Fore.YELLOW}Component Breakdown:{Style.RESET_ALL}")

        component_order = [
            'stt_total',
            'memory_context_retrieval',
            'llm_total',
            'llm_time_to_first_token',
            'tts_total',
            'expression_update',
            'memory_save_message'
        ]

        for component in component_order:
            if component in stats:
                c = stats[component]
                print(f"  {component:30s}: {c['avg']:6.3f}s "
                      f"(min: {c['min']:.3f}s, max: {c['max']:.3f}s)")

        # TTS segments
        tts_segments = [k for k in stats.keys() if k.startswith('tts_segment_')]
        if tts_segments:
            print(f"\n{Fore.YELLOW}TTS Segments:{Style.RESET_ALL}")
            for seg in sorted(tts_segments):
                s = stats[seg]
                print(f"  {seg}: {s['avg']:.3f}s")

        print(f"\n{Fore.CYAN}{'─'*70}{Style.RESET_ALL}\n")


class IntegrationTest:
    """
    Main integration test orchestrator
    Tests all components with comprehensive latency monitoring
    """

    def __init__(self, config: dict):
        """
        Initialize integration test

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.latency_monitor = LatencyMonitor()
        self.session_id = None
        self.user_id = None

        # Component references
        self.user_memory = None
        self.conversation_history = None
        self.ollama_client = None
        self.conversation_manager = None
        self.tts_engine = None
        self.stt_engine = None
        self.emotion_display = None
        self.voice_pipeline = None
        self.stt_mute_until = 0.0
        # Base mute window to avoid STT hearing petting TTS
        self.gesture_tts_mute_secs = 6.0
        self.input_mode = 'text'  # 'text' or 'voice'

        # Initialize all components
        print(f"{Fore.CYAN}Initializing components...{Style.RESET_ALL}")
        self._init_memory()
        self._init_llm()
        self._init_tts()
        self._init_expression()
        self._init_voice_pipeline()
        print(f"{Fore.GREEN}All components initialized!{Style.RESET_ALL}\n")

    def _init_memory(self):
        """Initialize memory system and create test user"""
        try:
            self.latency_monitor.start_timer('init_memory')

            self.user_memory, self.conversation_history = initialize_memory(self.config)

            # Create or get test user
            test_user = self.user_memory.get_user_by_name("TestUser")
            if not test_user:
                self.user_id = self.user_memory.create_user("TestUser")
                logger.info(f"Created test user with ID: {self.user_id}")
            else:
                self.user_id = test_user['user_id']
                logger.info(f"Using existing test user with ID: {self.user_id}")

            # Generate session ID
            self.session_id = self.conversation_history.generate_session_id()

            self.latency_monitor.end_timer('init_memory')
            print(f"  ✅ Memory System (user_id: {self.user_id})")

        except Exception as e:
            print(f"  ❌ Memory System: {e}")
            logger.error(f"Memory initialization failed: {e}", exc_info=True)
            raise

    def _init_llm(self):
        """Initialize LLM client and conversation manager"""
        try:
            self.latency_monitor.start_timer('init_llm')

            self.ollama_client = OllamaClient(self.config)

            self.conversation_manager = ConversationManager(
                self.config,
                user_memory=self.user_memory,
                conversation_history=self.conversation_history
            )

            self.latency_monitor.end_timer('init_llm')

            status = "OK" if self.ollama_client.is_available else "UNAVAILABLE"
            model = self.config['llm']['ollama']['model']
            print(f"  ✅ LLM ({model}) - Status: {status}")

        except Exception as e:
            print(f"  ❌ LLM: {e}")
            logger.error(f"LLM initialization failed: {e}", exc_info=True)
            raise

    def _init_tts(self):
        """Initialize TTS engine"""
        try:
            self.latency_monitor.start_timer('init_tts')

            self.tts_engine = TTSEngine(self.config)

            self.latency_monitor.end_timer('init_tts')

            provider = self.config['speech']['tts']['provider']
            print(f"  ✅ TTS ({provider})")

        except Exception as e:
            print(f"  ❌ TTS: {e}")
            logger.error(f"TTS initialization failed: {e}", exc_info=True)
            raise

    def _init_expression(self):
        """Initialize emotion display"""
        try:
            self.latency_monitor.start_timer('init_expression')

            self.emotion_display = EmotionDisplay(self.config)
            # Wire gesture effects into TTS/sound pipeline
            self.emotion_display.set_effect_callback(self._on_gesture_effect)
            self.emotion_display.start()

            self.latency_monitor.end_timer('init_expression')
            print(f"  ✅ Expression Display")

        except Exception as e:
            print(f"  ⚠️  Expression Display: {e} (non-critical)")
            logger.warning(f"Expression display initialization failed: {e}")
            self.emotion_display = None  # Continue without display

    def _init_voice_pipeline(self):
        """Initialize voice pipeline for STT"""
        try:
            self.latency_monitor.start_timer('init_voice_pipeline')

            from llm.voice_pipeline import VoicePipeline

            self.voice_pipeline = VoicePipeline(self.config)

            # Register speech detection callbacks
            self.voice_pipeline.set_speech_callbacks(
                on_start=self._on_speech_start,
                on_end=self._on_speech_end
            )
            self.voice_pipeline.set_transcription_callback(
                self._on_transcription_complete
            )

            self.latency_monitor.end_timer('init_voice_pipeline')
            print(f"  ✅ Voice Pipeline (STT)")

        except Exception as e:
            print(f"  ⚠️  Voice Pipeline: {e} (falling back to text mode)")
            logger.warning(f"Voice pipeline initialization failed: {e}")
            self.voice_pipeline = None

    def _on_gesture_effect(self, effect: dict):
        """
        Handle touch/petting gesture effects: speak or play sound.
        """
        if not effect:
            return

        # Emotion is already handled in EmotionDisplay; only handle side effects here.
        speak_text = effect.get('speak')
        sound_path = effect.get('sound')
        emotion = effect.get('emotion')

        if speak_text and self.tts_engine:
            try:
                # Estimate mute window to cover petting TTS playback
                est_secs = max(
                    self.gesture_tts_mute_secs,
                    (len(speak_text) / 6.0) + 3.0
                )
                self.stt_mute_until = time.time() + est_secs
                if self.voice_pipeline:
                    self.voice_pipeline.set_mute(est_secs)
                self.tts_engine.speak(speak_text, emotion=emotion, wait=False)
            except Exception as exc:  # pragma: no cover
                logger.error(f"Gesture TTS failed: {exc}")

        if sound_path:
            # If audio output queue/player exists, route here. Not present in this test harness.
            logger.info("Gesture sound requested: %s (not wired to player in this script)", sound_path)
    def _on_speech_start(self):
        """Callback when speech detection starts recording"""
        if self.emotion_display:
            self.emotion_display.set_listening(True)
        logger.debug("Speech detected - listening state activated")

    def _on_speech_end(self):
        """Callback when speech ends (silence detected)"""
        # Note: Don't deactivate listening yet - transcription still in progress
        logger.debug("Speech ended - processing transcription")

    def _on_transcription_complete(self, result: dict):
        """Callback when transcription completes"""
        if time.time() < self.stt_mute_until:
            logger.debug("Ignoring transcription during gesture TTS mute window")
            return
        if self.emotion_display:
            self.emotion_display.set_listening(False)
        logger.debug(f"Transcription complete: {result.get('text', '')}")

    def _choose_input_mode(self):
        """Let user choose between text and voice input"""
        if self.voice_pipeline is None:
            print(f"{Fore.YELLOW}Voice pipeline unavailable, "
                  f"using text mode{Style.RESET_ALL}")
            self.input_mode = 'text'
            return

        print(f"\n{Fore.CYAN}Select Input Mode:{Style.RESET_ALL}")
        print(f"  1. Voice (microphone + STT)")
        print(f"  2. Text (keyboard)")

        while True:
            choice = input(f"{Fore.GREEN}Choice (1/2): "
                          f"{Style.RESET_ALL}").strip()
            if choice == '1':
                self.input_mode = 'voice'
                print(f"{Fore.GREEN}Voice mode enabled{Style.RESET_ALL}")
                break
            elif choice == '2':
                self.input_mode = 'text'
                print(f"{Fore.GREEN}Text mode enabled{Style.RESET_ALL}")
                break
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")

    def _get_user_input_voice(self):
        """
        Get user input via voice (microphone + STT)

        Returns:
            Transcribed text or None if cancelled
        """
        print(f"{Fore.CYAN}🎤 Listening... (speak now){Style.RESET_ALL}")

        # Start STT timing
        self.latency_monitor.start_timer('stt_total')

        # Start voice pipeline listening
        # (listening state will be activated by callback when speech detected)
        self.voice_pipeline.start()

        try:
            # Wait for transcription with timeout
            result = self.voice_pipeline.wait_for_transcription(timeout=30.0)

            if result and result.get('text'):
                transcription = result['text'].strip()
                confidence = result.get('confidence', 0.0)

                # End STT timing
                stt_time = self.latency_monitor.end_timer('stt_total')

                # Record STT confidence
                self.latency_monitor.record_metric('stt_confidence',
                                                   confidence)

                print(f"{Fore.GREEN}You (voice): {transcription}"
                      f"{Style.RESET_ALL}")
                print(f"{Fore.CYAN}[STT: {stt_time:.2f}s, "
                      f"confidence: {confidence:.2f}]{Style.RESET_ALL}")

                return transcription
            else:
                print(f"{Fore.YELLOW}No speech detected{Style.RESET_ALL}")
                # Cancel timer if no speech
                if 'stt_total' in self.latency_monitor.current_timers:
                    del self.latency_monitor.current_timers['stt_total']
                return None

        except Exception as e:
            logger.error(f"Voice input error: {e}", exc_info=True)
            print(f"{Fore.RED}Voice input failed: {e}{Style.RESET_ALL}")
            # Cancel timer on error
            if 'stt_total' in self.latency_monitor.current_timers:
                del self.latency_monitor.current_timers['stt_total']
            return None

        finally:
            # Stop voice pipeline
            # (listening state will be deactivated by callback when transcription completes)
            self.voice_pipeline.stop()

    def _process_conversation_turn(self, user_text: str):
        """
        Process one conversation turn with comprehensive latency tracking

        Args:
            user_text: User's input text
        """
        turn_start = time.time()

        # 1. Memory - Load context
        self.latency_monitor.start_timer('memory_context_retrieval')
        context = self.conversation_history.get_recent_context(
            self.user_id, limit=10
        )
        self.latency_monitor.end_timer('memory_context_retrieval')

        # 2. LLM - Generate response with streaming
        self.latency_monitor.start_timer('llm_total')
        self.latency_monitor.start_timer('llm_time_to_first_token')

        segments = []
        first_token_recorded = False

        print(f"{Fore.CYAN}Bot: {Style.RESET_ALL}", end='', flush=True)

        try:
            for emotion, text in self.conversation_manager.stream_generate_with_personality(
                user_text, self.user_id
            ):
                if not first_token_recorded:
                    ttft = self.latency_monitor.end_timer('llm_time_to_first_token')
                    logger.debug(f"Time to first token: {ttft:.3f}s")
                    first_token_recorded = True

                segments.append((emotion, text))
                print(f"[{emotion}] {text} ", end='', flush=True)

        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            # Fallback response
            segments = [('happy', "I'm having trouble thinking right now!")]
            print(f"[happy] I'm having trouble thinking right now! ", end='', flush=True)

        print()  # New line after bot response

        llm_duration = self.latency_monitor.end_timer('llm_total')

        # Calculate tokens per second if available
        if llm_duration > 0 and segments:
            response_text = ' '.join([text for _, text in segments])
            # Rough token estimate (4 chars per token)
            estimated_tokens = len(response_text) / 4
            tokens_per_second = estimated_tokens / llm_duration
            self.latency_monitor.record_metric('tokens_per_second', tokens_per_second)

        # 3. Memory - Save conversation
        self.latency_monitor.start_timer('memory_save_message')

        # Save user message
        self.conversation_history.save_message(
            self.user_id, self.session_id, 'user', user_text
        )

        # Save assistant response
        if segments:
            response_text = ' '.join([text for _, text in segments])
            final_emotion = segments[-1][0] if segments else 'happy'
            self.conversation_history.save_message(
                self.user_id, self.session_id, 'assistant',
                response_text, emotion=final_emotion
            )

        self.latency_monitor.end_timer('memory_save_message')

        # 4. TTS - Speak segments (emotion display updated per segment)
        tts_start = time.time()
        self.latency_monitor.start_timer('tts_total')

        for i, (emotion, text) in enumerate(segments):
            self.latency_monitor.start_timer(f'tts_segment_{i}')

            # Update display to match segment emotion
            if self.emotion_display:
                self.latency_monitor.start_timer('expression_update')
                self.emotion_display.set_emotion(emotion, transition_duration=0.3)
                self.latency_monitor.end_timer('expression_update')
                self.emotion_display.set_speaking(True)

            try:
                self.tts_engine.speak(text, emotion=emotion, wait=True)
            except Exception as e:
                logger.error(f"TTS error: {e}", exc_info=True)

            if self.emotion_display:
                self.emotion_display.set_speaking(False)

            self.latency_monitor.end_timer(f'tts_segment_{i}')

        self.latency_monitor.end_timer('tts_total')

        # 6. End-to-end timing
        turn_end = time.time()
        end_to_end = turn_end - turn_start
        self.latency_monitor.record_metric('end_to_end_latency', end_to_end)

        # Perceived latency (time to first audio playback)
        if segments:
            perceived = tts_start - turn_start
            self.latency_monitor.record_metric('perceived_latency', perceived)

    def run_interactive_demo(self):
        """Main interactive conversation loop"""
        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🤖 COMPANION BOT - FULL INTEGRATION TEST{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"\n{Fore.GREEN}Test Mode: Interactive Demo{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Session ID: {self.session_id}{Style.RESET_ALL}")

        # Choose input mode
        self._choose_input_mode()

        # Display instructions based on mode
        print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
        if self.input_mode == 'voice':
            print("  - Speak into microphone to chat")
            print("  - Say 'statistics' or 'stats' to see latency metrics")
            print("  - Say 'quit' or 'exit' to finish")
        else:
            print("  - Type your message to chat")
            print("  - Type 'stats' to see latency statistics")
            print("  - Type 'quit' or 'exit' to finish and save report")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}\n")

        conversation_count = 0

        while True:
            try:
                # Get user input based on mode
                if self.input_mode == 'voice':
                    user_input = self._get_user_input_voice()

                    # Handle empty or None
                    if not user_input:
                        continue

                else:
                    # Text mode
                    user_input = input(f"{Fore.GREEN}You: "
                                      f"{Style.RESET_ALL}").strip()

                    if not user_input:
                        continue

                # Handle commands (works for both voice and text)
                if user_input.lower() in ['quit', 'exit', 'statistics',
                                          'stats']:
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    elif user_input.lower() in ['statistics', 'stats']:
                        self.latency_monitor.print_summary()
                        continue

                # Process conversation turn
                print(f"{Fore.YELLOW}[Processing...]{Style.RESET_ALL}")
                self._process_conversation_turn(user_input)

                conversation_count += 1

                # Print latency for this turn
                if self.latency_monitor.metrics.get('end_to_end_latency'):
                    latest = self.latency_monitor.metrics['end_to_end_latency'][-1]
                    print(f"{Fore.CYAN}[End-to-End: {latest:.2f}s]{Style.RESET_ALL}\n")

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
                break

            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                logger.error(f"Error in conversation turn: {e}", exc_info=True)
                continue

        # Save final report
        self._save_final_report(conversation_count)

    def _save_final_report(self, conversation_count: int):
        """
        Generate and save final JSON report

        Args:
            conversation_count: Number of conversation turns
        """
        report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'session_id': self.session_id,
                'user_id': self.user_id,
                'conversation_count': conversation_count,
                'components_tested': ['Memory', 'LLM', 'TTS', 'Expression']
            },
            'latency_metrics': self.latency_monitor.get_statistics(),
            'component_status': {
                'memory': 'OK' if self.user_memory else 'ERROR',
                'llm': 'OK' if self.ollama_client.is_available else 'UNAVAILABLE',
                'tts': 'OK' if self.tts_engine else 'ERROR',
                'expression': 'OK' if self.emotion_display else 'WARNING'
            },
            'configuration': {
                'llm_model': self.config['llm']['ollama']['model'],
                'tts_provider': self.config['speech']['tts']['provider'],
                'streaming_enabled': self.config['llm']['streaming']['enabled']
            }
        }

        # Save to JSON
        report_path = Path('data/logs/integration_test_report.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n{Fore.GREEN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Report saved to: {report_path}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}")

        # Print summary
        self.latency_monitor.print_summary()

    def cleanup(self):
        """Clean up all components"""
        logger.info("Cleaning up components...")

        if self.voice_pipeline:
            try:
                self.voice_pipeline.cleanup()
            except Exception as e:
                logger.error(f"Voice pipeline cleanup error: {e}")

        if self.emotion_display:
            try:
                self.emotion_display.cleanup()
            except Exception as e:
                logger.error(f"Expression cleanup error: {e}")

        if self.tts_engine:
            try:
                self.tts_engine.cleanup()
            except Exception as e:
                logger.error(f"TTS cleanup error: {e}")

        logger.info("Cleanup complete")


def main():
    """Main entry point"""
    # Initialize colorama if available
    if COLORAMA_AVAILABLE:
        init(autoreset=True)

    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        return 1

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return 1

    # Create and run test
    test = None
    try:
        test = IntegrationTest(config)
        test.run_interactive_demo()
        return 0

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test interrupted{Style.RESET_ALL}")
        return 0

    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

    finally:
        if test:
            test.cleanup()


if __name__ == "__main__":
    sys.exit(main())
