"""
image_generator.py
──────────────────
Resilient image generation with a 4-level fallback chain:

  1. FLUX.1-schnell        (HF — best free quality)
  2. SDXL Base 1.0         (HF — proven workhorse)
  3. Stable Diffusion 2.1  (HF — lightweight fallback)
  4. Pollinations.ai       (zero-auth HTTP GET — final safety net)

If every HF model fails, Pollinations.ai always delivers.
"""
import logging
import time
import urllib.parse
from pathlib import Path

import requests
from huggingface_hub import InferenceClient
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import HUGGINGFACE_API_KEY, GENERATED_IMAGES_DIR, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.image_generator")

# ── Model chain — tried in order ──────────────────────────────────────────────
HF_MODELS = [
    "black-forest-labs/FLUX.1-schnell",        # Best free quality, actively maintained
    "stabilityai/stable-diffusion-xl-base-1.0", # Proven workhorse
    "stabilityai/stable-diffusion-2-1",         # Lightweight fallback
]

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width=768&height=1350&nologo=true&seed={seed}"


class ImageGenerator:
    def __init__(self) -> None:
        if not HUGGINGFACE_API_KEY:
            raise EnvironmentError("HUGGINGFACE_API_KEY is not set.")
        self._client = InferenceClient(
            token=HUGGINGFACE_API_KEY,
            provider="hf-inference",
        )

    # ──────────────────────────────────────────────────────────────────────────
    def generate(self, image_prompt: str, style: str, mood: str, day: int) -> Path:
        """
        Try each model in the fallback chain.
        Returns the saved image path on first success.
        Raises RuntimeError only if every option is exhausted.
        """
        full_prompt = self._build_prompt(image_prompt, style, mood)
        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}.png"

        # ── Try each HF model ──────────────────────────────────────────────
        for model in HF_MODELS:
            try:
                logger.info("Trying HF model: %s", model)
                image = self._try_hf_model(model, full_prompt)
                image.save(str(file_path))
                logger.info("✅ Image generated via %s → %s", model, file_path)
                return file_path
            except Exception as exc:
                logger.warning("⚠️  Model %s failed: %s — trying next...", model, exc)
                time.sleep(3)

        # ── Final safety net: Pollinations.ai ─────────────────────────────
        logger.warning("All HF models failed. Falling back to Pollinations.ai...")
        try:
            self._try_pollinations(full_prompt, day, file_path)
            logger.info("✅ Image generated via Pollinations.ai → %s", file_path)
            return file_path
        except Exception as exc:
            logger.error("❌ Pollinations.ai also failed: %s", exc)
            raise RuntimeError(
                "All image generation sources exhausted (HF chain + Pollinations.ai)."
            ) from exc

    # ──────────────────────────────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        reraise=True,
    )
    def _try_hf_model(self, model: str, prompt: str):
        """Call HF InferenceClient for a single model. Returns PIL Image."""
        return self._client.text_to_image(prompt, model=model)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    def _try_pollinations(self, prompt: str, day: int, file_path: Path) -> None:
        """Fetch image from Pollinations.ai and write to file_path."""
        encoded = urllib.parse.quote(prompt)
        url = POLLINATIONS_URL.format(prompt=encoded, seed=day)
        logger.info("Requesting Pollinations.ai: %s", url[:80] + "...")

        response = requests.get(url, timeout=120)
        if response.status_code != 200:
            raise RuntimeError(f"Pollinations returned {response.status_code}")
        if not response.content:
            raise RuntimeError("Pollinations returned empty content.")

        file_path.write_bytes(response.content)

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_prompt(image_prompt: str, style: str, mood: str) -> str:
        return (
            "Vertical format (4:5 aspect ratio, optimized for Instagram post). "
            f"{image_prompt}. "
            f"Art style: {style}. "
            f"Mood and atmosphere: {mood}. "
            "Cinematic composition, ultra-detailed, vibrant colors, "
            "suitable for Instagram feed."
        )
