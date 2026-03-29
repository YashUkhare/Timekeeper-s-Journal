import logging
from pathlib import Path

from app.config import EXCEL_FILE_PATH
from app.excel_reader import ExcelReader, StoryRow
from app.image_generator import ImageGenerator
from app.caption_generator import CaptionGenerator
from app.image_uploader import ImageUploader
from app.instagram_poster import InstagramPoster
from app import pending_store

logger = logging.getLogger("instagram_bot.bot")


class InstagramBot:
    """Orchestrates the full daily posting pipeline."""

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

        story = self._excel.get_today_story()
        if story is None:
            logger.warning("No pending stories found. Nothing to post today.")
            return

        try:
            # 1. Generate image
            image_path = self._image_gen.generate(
                image_prompt=story.image_prompt,
                style=story.style,
                mood=story.mood,
                day=story.day,
            )
            logger.info("✅ Image generated: %s", image_path)

            # 2. Generate caption
            caption = self._caption_gen.generate(
                caption_context=story.caption_context,
                next_day_teaser=story.next_day_teaser,
                hashtags=story.hashtags,
                day=story.day,
                title=story.title,
            )
            logger.info("✅ Caption generated.")

            # 3. Upload image to Cloudinary
            public_url = self._uploader.upload(image_path, story.day)
            logger.info("✅ Image uploaded: %s", public_url)

            # 4. Post to Instagram
            self._publish(public_url, caption, story.index, story.day)

        except Exception as exc:
            logger.error("❌ Pipeline failed for Day %d: %s", story.day, exc, exc_info=True)
            self._excel.mark_failed(story.index)
            raise

        finally:
            logger.info("=" * 60)

    # ──────────────────────────────────────────────────────────────────────────
    def retry_publish(self) -> None:
        """Read pending_publish.json and attempt Instagram publish only."""
        logger.info("=" * 60)
        logger.info("Retry-publish pipeline started.")

        pending = pending_store.load()
        if not pending:
            logger.info("No pending publish found. Nothing to do.")
            return

        try:
            self._publish(
                image_url=pending["image_url"],
                caption=pending["caption"],
                row_index=pending["row_index"],
                day=pending["day"],
            )
        except Exception as exc:
            logger.error("❌ Retry publish failed for Day %s: %s", pending.get("day"), exc, exc_info=True)
            raise

        finally:
            logger.info("=" * 60)

    # ──────────────────────────────────────────────────────────────────────────
    def _publish(self, image_url: str, caption: str, row_index: int, day: int) -> None:
        """Post to Instagram, update Excel, and clear any pending file."""
        try:
            media_id = self._poster.post(image_url=image_url, caption=caption)
            logger.info("✅ Posted to Instagram. Media ID: %s", media_id)
        except Exception:
            # Save for retry workflow before re-raising
            pending_store.save(image_url, caption, row_index, day)
            logger.warning("⚠️  Instagram post failed. Saved to pending_publish.json for retry.")
            raise

        # Success — update Excel and clear pending file
        self._excel.mark_posted(row_index)
        pending_store.clear()
        logger.info("✅ Excel updated → Posted (Day %d).", day)
