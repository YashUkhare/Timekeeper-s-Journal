import logging
from pathlib import Path

from app.config import EXCEL_FILE_PATH
from app.excel_reader import ExcelReader
from app.image_generator import ImageGenerator
from app.caption_generator import CaptionGenerator
from app.caption_card_generator import CaptionCardGenerator
from app.image_uploader import ImageUploader
from app.instagram_poster import InstagramPoster
from app import pending_store

logger = logging.getLogger("instagram_bot.bot")


class InstagramBot:
    """Orchestrates the full daily posting pipeline."""

    def __init__(self) -> None:
        self._excel        = ExcelReader(EXCEL_FILE_PATH)
        self._image_gen    = ImageGenerator()
        self._caption_gen  = CaptionGenerator()
        self._card_gen     = CaptionCardGenerator()
        self._uploader     = ImageUploader()
        self._poster       = InstagramPoster()

    # ──────────────────────────────────────────────────────────────────────────
    def run(self) -> None:
        logger.info("=" * 60)
        logger.info("Instagram Bot pipeline started.")

        story = self._excel.get_today_story()
        if story is None:
            logger.warning("No pending stories found. Nothing to post today.")
            return

        try:
            # 1. Generate scene image (Slide 1)
            image_path = self._image_gen.generate(
                image_prompt=story.image_prompt,
                style=story.style,
                mood=story.mood,
                day=story.day,
            )
            logger.info("✅ Scene image generated: %s", image_path)

            # 2. Generate caption text
            caption = self._caption_gen.generate(
                caption_context=story.caption_context,
                next_day_teaser=story.next_day_teaser,
                hashtags=story.hashtags,
                day=story.day,
                title=story.title,
            )
            logger.info("✅ Caption text generated.")

            # 3. Render caption card image (Slide 2)
            card_path = self._card_gen.generate(
                caption=caption,
                day=story.day,
                title=story.title,
                style=story.style,
                mood=story.mood,
            )
            logger.info("✅ Caption card generated: %s", card_path)

            # 4. Upload both images to Cloudinary
            image_url = self._uploader.upload(image_path, f"day_{story.day:03d}")
            card_url  = self._uploader.upload(card_path,  f"day_{story.day:03d}_caption")
            logger.info("✅ Images uploaded → %s | %s", image_url, card_url)

            # 5. Post carousel to Instagram
            self._publish(
                image_url=image_url,
                card_url=card_url,
                hashtags=story.hashtags,
                row_index=story.index,
                day=story.day,
            )

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
                card_url=pending["card_url"],
                hashtags=pending["hashtags"],
                row_index=pending["row_index"],
                day=pending["day"],
            )
        except Exception as exc:
            logger.error("❌ Retry publish failed for Day %s: %s", pending.get("day"), exc, exc_info=True)
            raise

        finally:
            logger.info("=" * 60)

    # ──────────────────────────────────────────────────────────────────────────
    def _publish(
        self,
        image_url: str,
        card_url: str,
        hashtags: str,
        row_index: int,
        day: int,
    ) -> None:
        """Post carousel to Instagram, update Excel, clear any pending file."""
        try:
            media_id = self._poster.post(
                image_url=image_url,
                caption_card_url=card_url,
                hashtags=hashtags,
            )
            logger.info("✅ Carousel posted. Media ID: %s", media_id)
        except Exception:
            pending_store.save(
                image_url=image_url,
                card_url=card_url,
                hashtags=hashtags,
                row_index=row_index,
                day=day,
            )
            logger.warning("⚠️  Instagram post failed. Saved to pending_publish.json for retry.")
            raise

        self._excel.mark_posted(row_index)
        pending_store.clear()
        logger.info("✅ Excel updated → Posted (Day %d).", day)
