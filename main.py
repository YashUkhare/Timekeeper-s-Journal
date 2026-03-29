"""
Instagram Story Bot — Entry Point
----------------------------------
Usage:
    python main.py              → Start the scheduler (runs daily at 00:05 UTC)
    python main.py --now        → Run the full pipeline immediately
    python main.py --retry      → Only retry a failed Instagram publish
"""

import argparse
import sys

from app.config import setup_logging, validate_config


def main() -> None:
    logger = setup_logging()

    missing = validate_config()
    if missing:
        logger.error("Missing required environment variables: %s", missing)
        logger.error("Please fill in your .env file and restart.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Instagram Story Bot")
    parser.add_argument("--now", action="store_true", help="Run the full pipeline immediately.")
    parser.add_argument("--retry", action="store_true", help="Retry a failed Instagram publish only.")
    args = parser.parse_args()

    from app.bot import InstagramBot
    bot = InstagramBot()

    if args.retry:
        logger.info("Running publish-only retry (--retry flag).")
        bot.retry_publish()
    elif args.now:
        logger.info("Running bot immediately (--now flag).")
        bot.run()
    else:
        logger.info("Starting scheduler...")
        from app.scheduler import run_scheduler
        run_scheduler()


if __name__ == "__main__":
    main()
