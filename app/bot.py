import logging
from pathlib import Path

from app.config import EXCEL_FILE_PATH
from app.excel_reader import ExcelReader, StoryRow
from app.image_generator import ImageGenerator
from app.caption_generator import CaptionGenerator
from app.image_uploader import ImageUploader
from app.instagram_poster import InstagramPoster

logger = logging.getLogger("instagram_bot.bot")


class InstagramBot:
    """Orchestrates the daily posting pipeline."""

    def __init__(self) -> None:
        self._excel = ExcelReader(EXCEL_FILE_PATH)
        self._image_gen = ImageGenerator()
        self._caption_gen = CaptionGenerator()
        self._uploader = ImageUploader()
        self._poster = InstagramPoster()

    # ──────────────────────────────────────────────────────────────────────────
    def run(self) -> None:
        logger.info("=" * 60)
        logger.info("Instagram Bot pipeline started.")

        # 1. Read today's story row
        story = self._excel.get_today_story()
        if story is None:
            logger.warning("No pending stories found. Nothing to post today.")
            return

        image_path: Path | None = None

        try:
            # 2. Generate image
            image_path = self._image_gen.generate(
                image_prompt=story.image_prompt,
                style=story.style,
                mood=story.mood,
                day=story.day,
            )
            logger.info("✅ Image generated: %s", image_path)

            # 3. Generate caption
            caption = self._caption_gen.generate(
                caption_context=story.caption_context,
                next_day_teaser=story.next_day_teaser,
                hashtags=story.hashtags,
                day=story.day,
                title=story.title,
            )
            logger.info("✅ Caption generated.")

            # 4. Upload image to Cloudinary (get public URL)
            public_url = self._uploader.upload(image_path, story.day)
            logger.info("✅ Image uploaded: %s", public_url)

            # 5. Post to Instagram
            media_id = self._poster.post(image_url=public_url, caption=caption)
            logger.info("✅ Posted to Instagram. Media ID: %s", media_id)

            # 6. Mark Excel row as posted
            self._excel.mark_posted(story.index)
            logger.info("✅ Excel updated → Posted (Day %d).", story.day)

        except Exception as exc:
            logger.error("❌ Pipeline failed for Day %d: %s", story.day, exc, exc_info=True)
            self._excel.mark_failed(story.index)
            raise

        finally:
            logger.info("=" * 60)
