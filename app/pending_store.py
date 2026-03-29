import json
import logging
from pathlib import Path

logger = logging.getLogger("instagram_bot.pending_store")

PENDING_FILE = Path("pending_publish.json")


def save(image_url: str, caption: str, row_index: int, day: int) -> None:
    """Persist a failed publish so the retry workflow can pick it up."""
    data = {
        "image_url": image_url,
        "caption": caption,
        "row_index": row_index,
        "day": day,
    }
    PENDING_FILE.write_text(json.dumps(data, indent=2))
    logger.info("Pending publish saved → %s", PENDING_FILE)


def load() -> dict | None:
    """Return pending publish data, or None if no file exists."""
    if not PENDING_FILE.exists():
        return None
    data = json.loads(PENDING_FILE.read_text())
    logger.info("Loaded pending publish for Day %s", data.get("day"))
    return data


def clear() -> None:
    """Delete the pending file after a successful publish."""
    if PENDING_FILE.exists():
        PENDING_FILE.unlink()
        logger.info("Pending publish file cleared.")
