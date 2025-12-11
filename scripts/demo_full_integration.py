#!/usr/bin/env python3
"""
Full System Integration Test
Tests all components (STT, LLM, TTS, Expression, Memory) with latency monitoring
"""

import os
import sys
import time
import json
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import defaultdict


sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from colorama import init, Fore, Style
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

    class Fore:
        CYAN = GREEN = YELLOW = RED = ''
    class Style:
        RESET_ALL = ''

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

import yaml


from llm.ollama_client import OllamaClient
from llm.conversation_manager import ConversationManager
from llm.tts_engine import TTSEngine
from llm.stt_engine import STTEngine
from expression import EmotionDisplay
from memory import initialize_memory


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


        if 'end_to_end_latency' in stats:
            e2e = stats['end_to_end_latency']
            print(f"{Fore.GREEN}End-to-End Latency:{Style.RESET_ALL}")
            print(f"  Average: {e2e['avg']:.3f}s")
            print(f"  Min: {e2e['min']:.3f}s | Max: {e2e['max']:.3f}s | "
                  f"P95: {e2e['p95']:.3f}s | Count: {e2e['count']}\n")


        if 'perceived_latency' in stats:
            perc = stats['perceived_latency']
            print(f"{Fore.GREEN}Perceived Latency (to first audio):{Style.RESET_ALL}")
            print(f"  Average: {perc['avg']:.3f}s")
            print(f"  Min: {perc['min']:.3f}s | Max: {perc['max']:.3f}s | "
                  f"P95: {perc['p95']:.3f}s\n")


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


        tts_segments = [k for k in stats.keys() if k.startswith('tts_segment_')]
        if tts_segments:
            print(f"\n{Fore.YELLOW}TTS Segments:{Style.RESET_ALL}")
            for seg in sorted(tts_segments):
                s = stats[seg]
                print(f"  {seg}: {s['avg']:.3f}s")

        print(f"\n{Fore.CYAN}{'─'*70}{Style.RESET_ALL}\n")


class ResourceMonitor:
    """
    Collects RAM usage snapshots for the main process and optional helpers.
    Results are only surfaced at the end with the final report.
    """

    def __init__(self):
        self.processes = {}
        self.samples = defaultdict(list)

        if PSUTIL_AVAILABLE:
            self.processes['main'] = psutil.Process(os.getpid())

    def attach_process_by_name(self, name_substring: str, label: str = None) -> bool:
        """Attach an external process (e.g., ollama) by name substring."""
        if not PSUTIL_AVAILABLE:
            return False

        label = label or name_substring
        proc = self._find_process(name_substring)
        if proc:
            self.processes[label] = proc
            return True
        return False

    def _find_process(self, substring: str):
        """Find first process whose name contains the substring."""
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info.get('name') or ''
                if substring.lower() in name.lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def capture_snapshot(self, label: str):
        """Record current RSS (MB) for all tracked processes."""
        if not PSUTIL_AVAILABLE:
            return

        for name, proc in list(self.processes.items()):
            try:
                rss_mb = proc.memory_full_info().rss / (1024 ** 2)
                self.samples[name].append({'label': label, 'mb': rss_mb})
            except (psutil.NoSuchProcess, psutil.AccessDenied):

                self.processes.pop(name, None)

    def get_statistics(self) -> dict:
        """Return aggregated stats per process and per checkpoint label."""
        if not PSUTIL_AVAILABLE:
            return {'enabled': False, 'reason': 'psutil not installed'}

        stats = {}
        for name, entries in self.samples.items():
            if not entries:
                continue

            values = np.array([e['mb'] for e in entries], dtype=float)
            label_stats = {}
            for lbl in {e['label'] for e in entries}:
                lbl_values = np.array(
                    [e['mb'] for e in entries if e['label'] == lbl],
                    dtype=float
                )
                label_stats[lbl] = {
                    'min_mb': float(np.min(lbl_values)),
                    'max_mb': float(np.max(lbl_values)),
                    'avg_mb': float(np.mean(lbl_values)),
                    'samples': int(len(lbl_values)),
                }

            stats[name] = {
                'overall': {
                    'min_mb': float(np.min(values)),
                    'max_mb': float(np.max(values)),
                    'avg_mb': float(np.mean(values)),
                    'samples': int(len(values)),
                },
                'by_label': label_stats
            }
        return stats

    def print_summary(self):
        """Print memory usage summary; meant to run once at the end."""
        if not PSUTIL_AVAILABLE:
            print(f"{Fore.YELLOW}RAM tracking disabled (psutil not installed){Style.RESET_ALL}")
            return

        stats = self.get_statistics()
        if not stats:
            print(f"{Fore.YELLOW}No RAM samples recorded{Style.RESET_ALL}")
            return
        if stats.get('enabled') is False:
            print(f"{Fore.YELLOW}RAM tracking disabled ({stats.get('reason')}){Style.RESET_ALL}")
            return

        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📈 RAM USAGE (MB){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")

        for name, data in stats.items():
            overall = data.get('overall', {})
            print(f"{Fore.GREEN}{name}:{Style.RESET_ALL} "
                  f"avg={overall.get('avg_mb', 0):.1f} "
                  f"max={overall.get('max_mb', 0):.1f} "
                  f"samples={overall.get('samples', 0)}")

            by_label = data.get('by_label', {})
            if by_label:
                print("  by checkpoint:")
                for lbl, lstats in sorted(by_label.items()):
                    print(f"    {lbl:12s} avg={lstats['avg_mb']:.1f} "
                          f"max={lstats['max_mb']:.1f} "
                          f"samples={lstats['samples']}")

        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}\n")


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
        self.resource_monitor = ResourceMonitor()
        self.session_id = None
        self.user_id = None


        self.user_memory = None
        self.conversation_history = None
        self.ollama_client = None
        self.conversation_manager = None
        self.tts_engine = None
        self.stt_engine = None
        self.emotion_display = None
        self.voice_pipeline = None
        self.stt_mute_until = 0.0

        self.gesture_tts_mute_secs = 6.0
        self.petting_lock = False

        self.input_mode = 'voice'
        self.shutdown_requested = False


        print(f"{Fore.CYAN}Initializing components...{Style.RESET_ALL}")
        self._init_memory()
        self._init_llm()
        self._init_tts()
        self._init_expression()
        self._init_voice_pipeline()
        self.resource_monitor.capture_snapshot('post_init')
        print(f"{Fore.GREEN}All components initialized!{Style.RESET_ALL}\n")

    def _init_memory(self):
        """Initialize memory system and create test user"""
        try:
            self.latency_monitor.start_timer('init_memory')

            self.user_memory, self.conversation_history = initialize_memory(self.config)


            test_user = self.user_memory.get_user_by_name("TestUser")
            if not test_user:
                self.user_id = self.user_memory.create_user("TestUser")
                logger.info(f"Created test user with ID: {self.user_id}")
            else:
                self.user_id = test_user['user_id']
                logger.info(f"Using existing test user with ID: {self.user_id}")


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

            self.resource_monitor.attach_process_by_name('ollama', label='ollama')

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

            self.emotion_display.set_effect_callback(self._on_gesture_effect)

            self.emotion_display.set_exit_callback(self._on_exit_button)
            self.emotion_display.start()

            self.latency_monitor.end_timer('init_expression')
            print(f"  ✅ Expression Display")

        except Exception as e:
            print(f"  ⚠️  Expression Display: {e} (non-critical)")
            logger.warning(f"Expression display initialization failed: {e}")
            self.emotion_display = None

    def _init_voice_pipeline(self):
        """Initialize voice pipeline for STT"""
        try:
            self.latency_monitor.start_timer('init_voice_pipeline')

            from llm.voice_pipeline import VoicePipeline

            self.voice_pipeline = VoicePipeline(self.config)


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


        speak_text = effect.get('speak')
        sound_path = effect.get('sound')
        emotion = effect.get('emotion')

        if speak_text and self.tts_engine:

            if self.petting_lock:
                return
            self.petting_lock = True
            try:

                if self.emotion_display:
                    self.emotion_display.command_queue.put({
                        'type': 'SET_PETTING',
                        'active': True
                    })


                if self.voice_pipeline:
                    self.voice_pipeline.pause_listening()

                if self.emotion_display:
                    self.emotion_display.set_listening(False)
                self.stt_mute_until = time.time() + 0.1


                self.tts_engine.speak(speak_text, emotion=emotion, wait=True)


                tail = 2.0
                self.stt_mute_until = time.time() + tail
                if self.voice_pipeline:
                    self.voice_pipeline.resume_listening()


                if self.emotion_display:
                    self.emotion_display.command_queue.put({
                        'type': 'SET_PETTING',
                        'active': False
                    })
            except Exception as exc:
                logger.error(f"Gesture TTS failed: {exc}")
            finally:
                self.petting_lock = False

        if sound_path:

            logger.info("Gesture sound requested: %s (not wired to player in this script)", sound_path)
    def _on_speech_start(self):
        """Callback when speech detection starts recording"""
        if self.emotion_display:
            self.emotion_display.set_listening(True)
        logger.debug("Speech detected - listening state activated")

    def _on_speech_end(self):
        """Callback when speech ends (silence detected)"""

        logger.debug("Speech ended - processing transcription")

    def _on_transcription_complete(self, result: dict):
        """Callback when transcription completes"""
        if self.emotion_display:
            self.emotion_display.set_listening(False)
        if time.time() < self.stt_mute_until:
            logger.debug("Ignoring transcription during gesture TTS mute window")
            return
        logger.debug(f"Transcription complete: {result.get('text', '')}")

    def _choose_input_mode(self):
        """Select input mode (auto voice for unattended runs)."""
        if self.voice_pipeline is None:
            print(f"{Fore.YELLOW}Voice pipeline unavailable, "
                  f"using text mode{Style.RESET_ALL}")
            self.input_mode = 'text'
            return


        self.input_mode = 'voice'
        print(f"{Fore.GREEN}Voice mode enabled (auto){Style.RESET_ALL}")

    def _get_user_input_voice(self):
        """
        Get user input via voice (microphone + STT)

        Returns:
            Transcribed text or None if cancelled
        """
        print(f"{Fore.CYAN}🎤 Listening... (speak now){Style.RESET_ALL}")


        self.latency_monitor.start_timer('stt_total')



        self.voice_pipeline.start()

        try:

            result = self.voice_pipeline.wait_for_transcription(timeout=30.0)

            if result and result.get('text'):
                transcription = result['text'].strip()
                confidence = result.get('confidence', 0.0)


                stt_time = self.latency_monitor.end_timer('stt_total')


                self.latency_monitor.record_metric('stt_confidence',
                                                   confidence)

                print(f"{Fore.GREEN}You (voice): {transcription}"
                      f"{Style.RESET_ALL}")
                print(f"{Fore.CYAN}[STT: {stt_time:.2f}s, "
                      f"confidence: {confidence:.2f}]{Style.RESET_ALL}")
                self.resource_monitor.capture_snapshot('stt')

                return transcription
            else:
                print(f"{Fore.YELLOW}No speech detected{Style.RESET_ALL}")

                if 'stt_total' in self.latency_monitor.current_timers:
                    del self.latency_monitor.current_timers['stt_total']
                return None

        except Exception as e:
            logger.error(f"Voice input error: {e}", exc_info=True)
            print(f"{Fore.RED}Voice input failed: {e}{Style.RESET_ALL}")

            if 'stt_total' in self.latency_monitor.current_timers:
                del self.latency_monitor.current_timers['stt_total']
            return None

        finally:


            self.voice_pipeline.stop()

    def _process_conversation_turn(self, user_text: str):
        """
        Process one conversation turn with comprehensive latency tracking

        Args:
            user_text: User's input text
        """
        turn_start = time.time()


        self.latency_monitor.start_timer('memory_context_retrieval')
        context = self.conversation_history.get_recent_context(
            self.user_id, limit=10
        )
        self.latency_monitor.end_timer('memory_context_retrieval')


        self.latency_monitor.start_timer('llm_total')
        self.latency_monitor.start_timer('llm_time_to_first_token')

        segments = []
        first_token_recorded = False
        tts_started = False

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


                if not tts_started:
                    tts_started = True
                    tts_start = time.time()
                    self.latency_monitor.start_timer('tts_total')
                seg_idx = len(segments) - 1
                self.latency_monitor.start_timer(f'tts_segment_{seg_idx}')

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

                self.latency_monitor.end_timer(f'tts_segment_{seg_idx}')

        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)

            segments = [('happy', "I'm having trouble thinking right now!")]
            print(f"[happy] I'm having trouble thinking right now! ", end='', flush=True)

        print()

        llm_duration = self.latency_monitor.end_timer('llm_total')
        self.resource_monitor.capture_snapshot('llm')


        if llm_duration > 0 and segments:
            response_text = ' '.join([text for _, text in segments])

            estimated_tokens = len(response_text) / 4
            tokens_per_second = estimated_tokens / llm_duration
            self.latency_monitor.record_metric('tokens_per_second', tokens_per_second)


        self.latency_monitor.start_timer('memory_save_message')


        self.conversation_history.save_message(
            self.user_id, self.session_id, 'user', user_text
        )


        if segments:
            response_text = ' '.join([text for _, text in segments])
            final_emotion = segments[-1][0] if segments else 'happy'
            self.conversation_history.save_message(
                self.user_id, self.session_id, 'assistant',
                response_text, emotion=final_emotion
            )

        self.latency_monitor.end_timer('memory_save_message')


        if first_token_recorded and tts_started:
            self.latency_monitor.end_timer('tts_total')
            self.resource_monitor.capture_snapshot('tts')
        elif not tts_started:

            self.latency_monitor.current_timers.pop('tts_total', None)


        turn_end = time.time()
        end_to_end = turn_end - turn_start
        self.latency_monitor.record_metric('end_to_end_latency', end_to_end)


        if first_token_recorded and tts_started:
            perceived = tts_start - turn_start
            self.latency_monitor.record_metric('perceived_latency', perceived)


        self.resource_monitor.capture_snapshot('turn_end')

    def run_interactive_demo(self):
        """Main interactive conversation loop"""
        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🤖 COMPANION BOT - FULL INTEGRATION TEST{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"\n{Fore.GREEN}Test Mode: Interactive Demo{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Session ID: {self.session_id}{Style.RESET_ALL}")


        self._choose_input_mode()


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
            if self.shutdown_requested:
                break
            try:

                if self.input_mode == 'voice':
                    user_input = self._get_user_input_voice()


                    if not user_input:
                        if self.shutdown_requested:
                            break
                        continue

                else:

                    user_input = input(f"{Fore.GREEN}You: "
                                      f"{Style.RESET_ALL}").strip()

                    if not user_input:
                        continue


                if user_input.lower() in ['quit', 'exit', 'statistics',
                                          'stats']:
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    elif user_input.lower() in ['statistics', 'stats']:
                        self.latency_monitor.print_summary()
                        continue


                print(f"{Fore.YELLOW}[Processing...]{Style.RESET_ALL}")
                self._process_conversation_turn(user_input)

                conversation_count += 1


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


        self._save_final_report(conversation_count)

    def _on_exit_button(self):
        """Handle GPIO exit button: request full shutdown."""
        logger.info("Exit button pressed - requesting shutdown")
        self.shutdown_requested = True

        if self.voice_pipeline:
            try:
                self.voice_pipeline.stop()
            except Exception as exc:
                logger.error("Voice pipeline stop error: %s", exc)

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
            'resource_usage': self.resource_monitor.get_statistics(),
            'configuration': {
                'llm_model': self.config['llm']['ollama']['model'],
                'tts_provider': self.config['speech']['tts']['provider'],
                'streaming_enabled': self.config['llm']['streaming']['enabled']
            }
        }


        report_path = Path('data/logs/integration_test_report.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n{Fore.GREEN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Report saved to: {report_path}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}")


        self.latency_monitor.print_summary()
        self.resource_monitor.print_summary()

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

    if COLORAMA_AVAILABLE:
        init(autoreset=True)


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
