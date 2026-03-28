"""
Instagram Story Bot — Entry Point
----------------------------------
Usage:
    python main.py              → Start the scheduler (runs daily at 00:05 UTC)
    python main.py --now        → Run the bot immediately (useful for testing)
"""

import argparse
import sys

from app.config import setup_logging, validate_config


def main() -> None:
    logger = setup_logging()

    # ── Validate environment ──────────────────────────────────────────────────
    missing = validate_config()
    if missing:
        logger.error("Missing required environment variables: %s", missing)
        logger.error("Please fill in your .env file and restart.")
        sys.exit(1)

    # ── Parse arguments ───────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="Instagram Story Bot")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run the posting pipeline immediately instead of waiting for the scheduler.",
    )
    args = parser.parse_args()

    if args.now:
        logger.info("Running bot immediately (--now flag).")
        from app.bot import InstagramBot
        InstagramBot().run()
    else:
        logger.info("Starting scheduler...")
        from app.scheduler import run_scheduler
        run_scheduler()


if __name__ == "__main__":
    main()
