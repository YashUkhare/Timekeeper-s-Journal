import logging
from pathlib import Path

import cloudinary
import cloudinary.uploader
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    MAX_RETRIES,
    RETRY_WAIT_SECONDS,
)

logger = logging.getLogger("instagram_bot.image_uploader")


class ImageUploader:
    """Uploads a local image to Cloudinary and returns a public URL."""

    def __init__(self) -> None:
        if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
            raise EnvironmentError("Cloudinary credentials are not fully set.")
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True,
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    def upload(self, image_path: Path, day: int) -> str:
        """Upload image and return the secure public URL."""
        logger.info("Uploading image to Cloudinary: %s", image_path)

        result = cloudinary.uploader.upload(
            str(image_path),
            public_id=f"instagram_bot/day_{day:03d}",
            overwrite=True,
            resource_type="image",
            format="jpg",
            transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )

        url: str = result["secure_url"]
        logger.info("Image uploaded → %s", url)
        return url
