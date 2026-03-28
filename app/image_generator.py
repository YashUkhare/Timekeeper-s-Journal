import logging
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import HUGGINGFACE_API_KEY, GENERATED_IMAGES_DIR, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.image_generator")

HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"


class ImageGenerator:
    def __init__(self) -> None:
        if not HUGGINGFACE_API_KEY:
            raise EnvironmentError("HUGGINGFACE_API_KEY is not set.")
        self._headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

    # ──────────────────────────────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    def generate(self, image_prompt: str, style: str, mood: str, day: int) -> Path:
        """Generate an image via Hugging Face SDXL and save it locally."""
        full_prompt = self._build_prompt(image_prompt, style, mood)
        logger.info("Generating image for Day %d | style='%s' mood='%s'", day, style, mood)

        response = requests.post(
            HF_API_URL,
            headers=self._headers,
            json={"inputs": full_prompt},
            timeout=120,
        )

        # 503 = model is loading/warming up — tenacity will retry automatically
        if response.status_code == 503:
            estimated = response.json().get("estimated_time", RETRY_WAIT_SECONDS)
            logger.warning(
                "Model is warming up (503). Estimated wait: %ss. Retrying...", estimated
            )
            raise RuntimeError(f"Model warming up, estimated time: {estimated}s")

        if response.status_code != 200:
            raise RuntimeError(
                f"Hugging Face API error {response.status_code}: {response.text[:300]}"
            )

        image_bytes = response.content
        if not image_bytes:
            raise RuntimeError("Hugging Face returned empty image bytes.")

        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}.png"
        file_path.write_bytes(image_bytes)

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
