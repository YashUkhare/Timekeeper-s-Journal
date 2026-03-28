import base64
import logging
from pathlib import Path

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import GOOGLE_API_KEY, GENERATED_IMAGES_DIR, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.image_generator")

# Gemini model that supports image generation
IMAGEN_MODEL = "imagen-3.0-generate-002"


class ImageGenerator:
    def __init__(self) -> None:
        if not GOOGLE_API_KEY:
            raise EnvironmentError("GOOGLE_API_KEY is not set.")
        genai.configure(api_key=GOOGLE_API_KEY)
        self._client = genai.ImageGenerationModel(IMAGEN_MODEL)

    # ──────────────────────────────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    def generate(self, image_prompt: str, style: str, mood: str, day: int) -> Path:
        """
        Generate an image via Gemini Imagen and save it locally.
        Returns the local file path.
        """
        full_prompt = self._build_prompt(image_prompt, style, mood)
        logger.info("Generating image for Day %d | style='%s' mood='%s'", day, style, mood)

        response = self._client.generate_images(
            prompt=full_prompt,
            number_of_images=1,
            aspect_ratio="9:16",          # Instagram Story format
            safety_filter_level="block_some",
            person_generation="allow_adult",
        )

        if not response.images:
            raise RuntimeError("Gemini returned no images.")

        image_data: bytes = response.images[0]._image_bytes
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}.png"
        file_path.write_bytes(image_data)

        logger.info("Image saved → %s", file_path)
        return file_path

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_prompt(image_prompt: str, style: str, mood: str) -> str:
        return (
            f"{image_prompt}. "
            f"Art style: {style}. "
            f"Mood and atmosphere: {mood}. "
            "Cinematic composition, ultra-detailed, vibrant colors, "
            "suitable for Instagram Story (9:16 vertical format)."
        )
