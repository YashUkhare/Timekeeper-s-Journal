import logging
import time

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

from app.config import (
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    INSTAGRAM_GRAPH_API_BASE,
    MAX_RETRIES,
    RETRY_WAIT_SECONDS,
)

logger = logging.getLogger("instagram_bot.instagram_poster")


class InstagramPoster:
    """Posts an image with caption to Instagram via the Graph API."""

    def __init__(self) -> None:
        if not INSTAGRAM_ACCESS_TOKEN:
            raise EnvironmentError("INSTAGRAM_ACCESS_TOKEN is not set.")
        if not INSTAGRAM_BUSINESS_ACCOUNT_ID:
            raise EnvironmentError("INSTAGRAM_BUSINESS_ACCOUNT_ID is not set.")

        self._base = INSTAGRAM_GRAPH_API_BASE
        self._token = INSTAGRAM_ACCESS_TOKEN
        self._account_id = INSTAGRAM_BUSINESS_ACCOUNT_ID

    # ──────────────────────────────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    def post(self, image_url: str, caption: str) -> str:
        """
        Upload image and publish to Instagram.
        Returns the Instagram media ID.
        """
        logger.info("Creating Instagram media container...")
        container_id = self._create_media_container(image_url, caption)

        # Instagram recommends waiting for the container to be ready
        logger.info("Waiting for media container to be ready (container_id=%s)...", container_id)
        self._wait_for_container(container_id)

        logger.info("Publishing media container...")
        media_id = self._publish_container(container_id)

        logger.info("Successfully posted to Instagram! Media ID: %s", media_id)
        return media_id

    # ──────────────────────────────────────────────────────────────────────────
    def _create_media_container(self, image_url: str, caption: str) -> str:
        url = f"{self._base}/{self._account_id}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self._token,
        }
        response = self._post(url, payload)
        return response["id"]

    def _wait_for_container(self, container_id: str, max_polls: int = 10) -> None:
        """Poll until the container status is FINISHED."""
        url = f"{self._base}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self._token,
        }
        for attempt in range(max_polls):
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status_code", "")

            if status == "FINISHED":
                logger.debug("Container ready after %d poll(s).", attempt + 1)
                return
            if status == "ERROR":
                raise RuntimeError(f"Instagram media container failed with status: {status}")

            logger.debug("Container status: %s. Retrying in 5s...", status)
            time.sleep(5)

        raise TimeoutError("Instagram media container did not become ready in time.")

    def _publish_container(self, container_id: str) -> str:
        url = f"{self._base}/{self._account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self._token,
        }
        response = self._post(url, payload)
        return response["id"]

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _post(url: str, payload: dict) -> dict:
        response = requests.post(url, data=payload, timeout=60)
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            raise

        if "error" in data:
            error = data["error"]
            raise RuntimeError(
                f"Instagram API error {error.get('code')}: {error.get('message')}"
            )

        response.raise_for_status()
        return data
