import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from app.config import SCHEDULER_HOUR, SCHEDULER_MINUTE
from app.bot import InstagramBot

logger = logging.getLogger("instagram_bot.scheduler")


def _job_listener(event) -> None:
    if event.exception:
        logger.error("Scheduled job FAILED: %s", event.exception)
    else:
        logger.info("Scheduled job completed successfully.")


def run_scheduler() -> None:
    """Start the blocking APScheduler that fires the bot daily at 00:05."""
    bot = InstagramBot()
    scheduler = BlockingScheduler(timezone="UTC")

    trigger = CronTrigger(hour=SCHEDULER_HOUR, minute=SCHEDULER_MINUTE)

    scheduler.add_job(
        func=bot.run,
        trigger=trigger,
        id="daily_instagram_post",
        name="Daily Instagram Story Post",
        misfire_grace_time=300,       # Allow 5-minute delay before skipping
        coalesce=True,                 # Merge missed jobs into one
        max_instances=1,               # Never run two instances simultaneously
    )

    scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    logger.info(
        "Scheduler started. Bot will post every day at %02d:%02d UTC.",
        SCHEDULER_HOUR,
        SCHEDULER_MINUTE,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        scheduler.shutdown(wait=False)
