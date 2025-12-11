#!/usr/bin/env python3
"""
Companion Bot - Main Entry Point
AI-powered pet companion robot with multimodal interaction
"""

import sys
import logging
import yaml
import signal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / 'src'))


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/companion.log')
    ]
)

logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent / 'config' / 'settings.yaml'

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Companion Bot Starting...")
    logger.info("=" * 60)


    config = load_config()


    Path("data/users").mkdir(parents=True, exist_ok=True)
    Path("data/conversations").mkdir(parents=True, exist_ok=True)
    Path("data/logs").mkdir(parents=True, exist_ok=True)

    try:

        from core.companion_bot import CompanionBot


        logger.info("Initializing companion bot...")
        bot = CompanionBot(config)


        def signal_handler(sig, frame):
            logger.info("\nShutdown signal received...")
            bot.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


        logger.info("Starting companion bot...")
        bot.start()


        logger.info("Companion bot is running! Press Ctrl+C to stop.")
        while bot.is_running:
            bot.update()

    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Companion bot stopped")


if __name__ == "__main__":
    main()
