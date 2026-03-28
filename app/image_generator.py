import base64
import logging
from pathlib import Path

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import GOOGLE_API_KEY, GENERATED_IMAGES_DIR, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.image_generator")

# Using the Imagen 4 Generate model from your dashboard
IMAGEN_MODEL = "imagen-4.0-generate-001"

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
        """Generate an image via Google Imagen 4 and save it locally."""
        full_prompt = self._build_prompt(image_prompt, style, mood)
        logger.info("Generating image for Day %d | style='%s' mood='%s'", day, style, mood)

        # 1. Call generate_images with Imagen 4
        response = self._client.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="3:4", # Vertical format for Instagram
            ),
        )

        # 2. Extract the image bytes securely
        image_bytes = None
        if response.generated_images and len(response.generated_images) > 0:
            image_bytes = response.generated_images[0].image.image_bytes

        if not image_bytes:
            raise RuntimeError("Imagen returned no image data in the response.")

        # 3. Save the file
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}.png"
        
        # Ensure the directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True) 
        file_path.write_bytes(image_bytes)

        logger.info("Image saved → %s", file_path)
        return file_path

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_prompt(image_prompt: str, style: str, mood: str) -> str:
        return (
            f"Generate a tall vertical portrait-format image. "
            f"{image_prompt}. "
            f"Art style: {style}. "
            f"Mood and atmosphere: {mood}. "
            "Cinematic composition, ultra-detailed, vibrant colors."
        )