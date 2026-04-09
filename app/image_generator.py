import logging
from pathlib import Path

from huggingface_hub import InferenceClient
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import HUGGINGFACE_API_KEY, GENERATED_IMAGES_DIR, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.image_generator")

HF_MODEL = "black-forest-labs/FLUX.1-dev"


class ImageGenerator:
    def __init__(self) -> None:
        if not HUGGINGFACE_API_KEY:
            raise EnvironmentError("HUGGINGFACE_API_KEY is not set.")
        self._client = InferenceClient(token=HUGGINGFACE_API_KEY, provider="hf-inference")

    # ──────────────────────────────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    def generate(self, image_prompt: str, style: str, mood: str, day: int) -> Path:
        """Generate an image via Hugging Face InferenceClient and save locally."""
        full_prompt = self._build_prompt(image_prompt, style, mood)
        logger.info("Generating image for Day %d | style='%s' mood='%s'", day, style, mood)

        # Returns a PIL Image directly — no manual HTTP or URL management needed
        image = self._client.text_to_image(full_prompt, model=HF_MODEL)

        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}.png"
        image.save(str(file_path))

        logger.info("Image saved → %s", file_path)
        return file_path

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_prompt(image_prompt: str, style: str, mood: str) -> str:
        return (
            "Tall vertical portrait format, 9:16 aspect ratio, more height than width. "
            f"{image_prompt}. "
            f"Art style: {style}. "
            f"Mood and atmosphere: {mood}. "
            "Cinematic composition, ultra-detailed, vibrant colors, "
            "suitable for Instagram Story."
        )
