import logging
import re
import unicodedata

from google import genai
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import GOOGLE_API_KEY, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.caption_generator")

GEMINI_TEXT_MODEL = "gemini-2.5-flash"


def strip_emojis(text: str) -> str:
    """Remove all emoji and pictographic characters from text."""
    return "".join(
        ch for ch in text
        if not unicodedata.category(ch).startswith("So")
        and not (0x1F300 <= ord(ch) <= 0x1FAFF)
        and not (0x2600  <= ord(ch) <= 0x27BF)
    ).strip()


class CaptionGenerator:
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
    def generate(
        self,
        caption_context: str,
        next_day_teaser: str,
        hashtags: str,
        day: int,
        title: str,
    ) -> str:
        """
        Generate a caption.
        Returns a string with three sections separated by double newlines:
            <story body>

            <teaser line>

            <hashtags>
        All emojis are stripped.
        """
        prompt = self._build_prompt(caption_context, next_day_teaser, hashtags, day, title)
        logger.info("Generating caption for Day %d – '%s'", day, title)

        response = self._client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        raw = response.text.strip()
        caption = strip_emojis(raw)

        logger.info("Caption generated (%d chars).", len(caption))
        return caption

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_prompt(
        caption_context: str,
        next_day_teaser: str,
        hashtags: str,
        day: int,
        title: str,
    ) -> str:
        return f"""You are a creative storyteller writing a daily AI time-travel series for Instagram.

Write a caption for Day {day}: "{title}".

Story context:
{caption_context}

Rules:
- Write a compelling 4-5 sentence story snippet
- Keep it under 180 words total
- NO emojis anywhere
- NO markdown formatting (no ** or ##)
- Dont use heavy words, keep the english simple to understand.
- Plain text only

Format the output EXACTLY like this (three sections, each separated by one blank line):

[Story text — 2-3 compelling sentences]

Tomorrow: {next_day_teaser}

{hashtags}"""
