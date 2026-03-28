import logging

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import GOOGLE_API_KEY, MAX_RETRIES, RETRY_WAIT_SECONDS

logger = logging.getLogger("instagram_bot.caption_generator")

GEMINI_TEXT_MODEL = "gemini-1.5-flash"


class CaptionGenerator:
    def __init__(self) -> None:
        if not GOOGLE_API_KEY:
            raise EnvironmentError("GOOGLE_API_KEY is not set.")
        genai.configure(api_key=GOOGLE_API_KEY)
        self._model = genai.GenerativeModel(GEMINI_TEXT_MODEL)

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
        Generate an Instagram caption via Gemini text model.
        Returns the formatted caption string.
        """
        prompt = self._build_prompt(caption_context, next_day_teaser, hashtags, day, title)
        logger.info("Generating caption for Day %d – '%s'", day, title)

        response = self._model.generate_content(prompt)
        caption = response.text.strip()

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
        return f"""You are a creative Instagram storyteller writing a daily time-travel series.

Write an engaging Instagram caption for Day {day}: "{title}".

Story context:
{caption_context}

Rules:
- Start with a captivating 2-3 sentence story snippet that hooks the reader
- Keep it under 200 words
- Use emojis sparingly but effectively (2-4 max)
- Add a line break before the teaser
- Add a line break before the hashtags
- Do NOT use markdown formatting like ** or ##

Format the output EXACTLY like this:
[Story text - 2-3 engaging sentences]

⏳ Tomorrow: {next_day_teaser}

{hashtags}"""
