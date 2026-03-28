import logging
from pathlib import Path

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import GOOGLE_API_KEY, GENERATED_IMAGES_DIR, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.image_generator")

IMAGEN_MODEL = "imagen-3.0-generate-002"


class ImageGenerator:
    def __init__(self) -> None:
        if not GOOGLE_API_KEY:
            raise EnvironmentError("GOOGLE_API_KEY is not set.")
        self._client = genai.Client(api_key=GOOGLE_API_KEY)

    # ──────────────────────────────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    def generate(self, image_prompt: str, style: str, mood: str, day: int) -> Path:
        """Generate an image via Gemini Imagen 3 and save it locally."""
        full_prompt = self._build_prompt(image_prompt, style, mood)
        logger.info("Generating image for Day %d | style='%s' mood='%s'", day, style, mood)

        response = self._client.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
                safety_filter_level="BLOCK_SOME",
                person_generation="ALLOW_ADULT",
            ),
        )

        if not response.generated_images:
            raise RuntimeError("Gemini Imagen returned no images.")

        image_bytes: bytes = response.generated_images[0].image.image_bytes
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}.png"
        file_path.write_bytes(image_bytes)

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