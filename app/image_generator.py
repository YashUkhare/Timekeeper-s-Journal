"""
image_generator.py

Image generation fallback chain:

1. Qwen Image via Hugging Face Inference Providers
2. FLUX.1-schnell via Hugging Face Inference Providers
3. Pollinations.ai

Permanent API errors (401/403/404/410) are NOT retried.
Transient failures (timeouts/429/5xx) may be retried.
"""

import logging
import time
import urllib.parse
from pathlib import Path

import requests
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from app.config import (
    HUGGINGFACE_API_KEY,
    GENERATED_IMAGES_DIR,
    MAX_RETRIES,
    RETRY_WAIT_SECONDS,
)

logger = logging.getLogger("instagram_bot.image_generator")


# Current models. provider="auto" decides where they actually run.
HF_MODELS = [
    "Qwen/Qwen-Image",
    "black-forest-labs/FLUX.1-schnell",
]

# Real 4:5 ratio
POLLINATIONS_URL = (
    "https://image.pollinations.ai/prompt/{prompt}"
    "?width=1080"
    "&height=1350"
    "&nologo=true"
    "&seed={seed}"
)


class ImageGenerator:

    def __init__(self) -> None:
        self._client = None

        if HUGGINGFACE_API_KEY:
            self._client = InferenceClient(
                token=HUGGINGFACE_API_KEY,
                provider="auto",
            )
        else:
            logger.warning(
                "HUGGINGFACE_API_KEY not configured. "
                "HF generation disabled; Pollinations fallback will be used."
            )

    def generate(
        self,
        image_prompt: str,
        style: str,
        mood: str,
        day: int,
    ) -> Path:

        full_prompt = self._build_prompt(
            image_prompt,
            style,
            mood,
        )

        GENERATED_IMAGES_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (
            GENERATED_IMAGES_DIR /
            f"day_{day:03d}.png"
        )

        # ---------------------------------------------------------
        # Hugging Face
        # ---------------------------------------------------------

        if self._client:

            for model in HF_MODELS:

                logger.info(
                    "Trying HF model: %s",
                    model,
                )

                try:
                    image = self._generate_hf(
                        model,
                        full_prompt,
                        day,
                    )

                    image.save(
                        file_path,
                        format="PNG",
                    )

                    logger.info(
                        "✅ Image generated via %s → %s",
                        model,
                        file_path,
                    )

                    return file_path

                except Exception as exc:
                    logger.warning(
                        "⚠️ Model %s failed: %s",
                        model,
                        exc,
                    )

        # ---------------------------------------------------------
        # Pollinations
        # ---------------------------------------------------------

        logger.warning(
            "HF models unavailable. "
            "Falling back to Pollinations.ai..."
        )

        try:
            self._generate_pollinations(
                full_prompt,
                day,
                file_path,
            )

            logger.info(
                "✅ Image generated via Pollinations.ai → %s",
                file_path,
            )

            return file_path

        except Exception as exc:

            logger.exception(
                "❌ Pollinations.ai failed."
            )

            raise RuntimeError(
                "All image generation providers failed."
            ) from exc

    # ---------------------------------------------------------
    # Hugging Face
    # ---------------------------------------------------------

    def _generate_hf(
        self,
        model: str,
        prompt: str,
        seed: int,
    ):
        """
        Retry transient errors only.

        Do NOT retry:
        400
        401
        403
        404
        410

        because another attempt will normally produce
        exactly the same result.
        """

        last_exception = None

        for attempt in range(1, MAX_RETRIES + 1):

            try:

                return self._client.text_to_image(
                    prompt,
                    model=model,
                    width=1080,
                    height=1350,
                    seed=seed,
                )

            except HfHubHTTPError as exc:

                last_exception = exc

                status = (
                    exc.response.status_code
                    if exc.response
                    else None
                )

                # Permanent errors
                if status in {
                    400,
                    401,
                    403,
                    404,
                    410,
                }:
                    logger.warning(
                        "Permanent HF error %s for %s. "
                        "Skipping retries.",
                        status,
                        model,
                    )

                    raise

                # Transient HTTP error
                logger.warning(
                    "HF attempt %s/%s failed "
                    "with HTTP %s.",
                    attempt,
                    MAX_RETRIES,
                    status,
                )

            except (
                requests.Timeout,
                requests.ConnectionError,
            ) as exc:

                last_exception = exc

                logger.warning(
                    "Transient network failure "
                    "attempt %s/%s: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)

        raise last_exception

    # ---------------------------------------------------------
    # Pollinations
    # ---------------------------------------------------------

    def _generate_pollinations(
        self,
        prompt: str,
        day: int,
        file_path: Path,
    ) -> None:

        encoded = urllib.parse.quote(
            prompt,
            safe="",
        )

        url = POLLINATIONS_URL.format(
            prompt=encoded,
            seed=day,
        )

        for attempt in range(1, 4):

            try:

                logger.info(
                    "Requesting Pollinations.ai "
                    "(attempt %s/3)",
                    attempt,
                )

                response = requests.get(
                    url,
                    timeout=120,
                )

                response.raise_for_status()

                if not response.content:
                    raise RuntimeError(
                        "Pollinations returned empty content."
                    )

                content_type = response.headers.get(
                    "Content-Type",
                    "",
                )

                if not content_type.startswith("image/"):
                    raise RuntimeError(
                        "Pollinations returned non-image "
                        f"content: {content_type}"
                    )

                file_path.write_bytes(
                    response.content
                )

                return

            except (
                requests.RequestException,
                RuntimeError,
            ):

                if attempt == 3:
                    raise

                time.sleep(10)

    # ---------------------------------------------------------

    @staticmethod
    def _build_prompt(
        image_prompt: str,
        style: str,
        mood: str,
    ) -> str:

        return (
            "Vertical Instagram artwork, "
            "4:5 aspect ratio. "
            f"{image_prompt}. "
            f"Art style: {style}. "
            f"Mood and atmosphere: {mood}. "
            "Cinematic composition, "
            "highly detailed, "
            "rich natural colors, "
            "professional lighting, "
            "strong visual storytelling, "
            "Instagram editorial quality. "
            "No text, no captions, no logos, "
            "no watermark."
        )
