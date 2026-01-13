"""
Crypto News Alert System - Main Entry Point
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

from .scheduler import AlertScheduler
from .utils.config import load_config
from .utils.logger import setup_logging

# Load environment variables
load_dotenv()


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logging.info("Shutdown signal received, stopping...")
    sys.exit(0)


async def main():
    """Main entry point for the alert collector."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("🚀 Crypto News Alert System Starting...")
    logger.info("=" * 50)
    
    # Load configuration
    config_dir = Path(__file__).parent.parent / "config"
    
    try:
        sources_config = load_config(config_dir / "sources.yaml")
        filters_config = load_config(config_dir / "filters.yaml")
        ntfy_config = load_config(config_dir / "ntfy.yaml")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    logger.info(f"📡 Loaded {len(sources_config.get('rss_feeds', []))} RSS feeds")
    logger.info(f"🐦 Loaded {len(sources_config.get('nitter_accounts', []))} Nitter accounts")
    logger.info(f"⚡ Loaded {len(sources_config.get('nostr_accounts', []))} Nostr accounts")
    
    # Initialize and run scheduler
    scheduler = AlertScheduler(
        sources_config=sources_config,
        filters_config=filters_config,
        ntfy_config=ntfy_config
    )
    
    try:
        await scheduler.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        await scheduler.shutdown()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main async loop
    asyncio.run(main())
