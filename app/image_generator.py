import base64
import logging
from pathlib import Path

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import GOOGLE_API_KEY, GENERATED_IMAGES_DIR, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.image_generator")

# Free-tier model for image generation (no billing required)
IMAGEN_MODEL = "gemini-2.0-flash-exp"


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
        """Generate an image via Gemini 2.0 Flash and save it locally."""
        full_prompt = self._build_prompt(image_prompt, style, mood)
        logger.info("Generating image for Day %d | style='%s' mood='%s'", day, style, mood)

        response = self._client.models.generate_content(
            model=IMAGEN_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["Text", "Image"],
            ),
        )

        # Find the image part in the response
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            raise RuntimeError("Gemini returned no image data in response.")

        # inline_data.data may be raw bytes or base64-encoded string
        if isinstance(image_bytes, str):
            image_bytes = base64.b64decode(image_bytes)

        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}.png"
        file_path.write_bytes(image_bytes)

        logger.info("Image saved → %s", file_path)
        return file_path

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_prompt(image_prompt: str, style: str, mood: str) -> str:
        return (
            f"Generate a tall vertical portrait-format image (taller than wide). "
            f"{image_prompt}. "
            f"Art style: {style}. "
            f"Mood and atmosphere: {mood}. "
            "Cinematic composition, ultra-detailed, vibrant colors, "
            "suitable for an Instagram Story."
        )
