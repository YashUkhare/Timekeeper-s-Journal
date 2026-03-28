import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_FILE_PATH = BASE_DIR / os.getenv("EXCEL_FILE_PATH", "data/story.xlsx")
GENERATED_IMAGES_DIR = BASE_DIR / os.getenv("GENERATED_IMAGES_DIR", "generated_images")
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Google Gemini ──────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ── Instagram ──────────────────────────────────────────────────────────────────
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
INSTAGRAM_GRAPH_API_VERSION = "v19.0"
INSTAGRAM_GRAPH_API_BASE = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}"

# ── Cloudinary (image hosting for Instagram) ──────────────────────────────────
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# ── Scheduler ─────────────────────────────────────────────────────────────────
SCHEDULER_HOUR = 0
SCHEDULER_MINUTE = 5

# ── Retry ─────────────────────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 10

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def validate_config() -> list[str]:
    """Return a list of missing required environment variables."""
    required = {
        "GOOGLE_API_KEY": GOOGLE_API_KEY,
        "INSTAGRAM_ACCESS_TOKEN": INSTAGRAM_ACCESS_TOKEN,
        "INSTAGRAM_BUSINESS_ACCOUNT_ID": INSTAGRAM_BUSINESS_ACCOUNT_ID,
        "CLOUDINARY_CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "CLOUDINARY_API_KEY": CLOUDINARY_API_KEY,
        "CLOUDINARY_API_SECRET": CLOUDINARY_API_SECRET,
    }
    return [name for name, value in required.items() if not value]


def setup_logging() -> logging.Logger:
    log_file = LOGS_DIR / "app.log"
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("instagram_bot")
