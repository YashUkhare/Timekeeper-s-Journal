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
    """Posts a 2-image carousel to Instagram via the Graph API."""

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
    def post(self, image_url: str, caption_card_url: str, hashtags: str) -> str:
        """
        Post a 2-slide carousel:
          Slide 1 → AI-generated scene image
          Slide 2 → Caption card image
        Returns the published media ID.
        """
        logger.info("Creating carousel child containers...")

        child_1 = self._create_child_container(image_url)
        logger.info("Child 1 ready: %s", child_1)
        self._wait_for_container(child_1)

        child_2 = self._create_child_container(caption_card_url)
        logger.info("Child 2 ready: %s", child_2)
        self._wait_for_container(child_2)

        logger.info("Creating carousel container...")
        carousel_id = self._create_carousel_container(
            children=[child_1, child_2],
            caption=hashtags,
        )

        logger.info("Waiting for carousel container...")
        self._wait_for_container(carousel_id)

        logger.info("Publishing carousel...")
        media_id = self._publish_container(carousel_id)

        logger.info("✅ Carousel posted! Media ID: %s", media_id)
        return media_id

    # ──────────────────────────────────────────────────────────────────────────
    def _create_child_container(self, image_url: str) -> str:
        """Create a single image child container (no caption)."""
        url = f"{self._base}/{self._account_id}/media"
        payload = {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": self._token,
        }
        return self._post(url, payload)["id"]

    def _create_carousel_container(self, children: list[str], caption: str) -> str:
        """Create a carousel container referencing child IDs."""
        url = f"{self._base}/{self._account_id}/media"
        payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": self._token,
        }
        return self._post(url, payload)["id"]

    def _wait_for_container(self, container_id: str, max_polls: int = 12) -> None:
        """Poll until container status is FINISHED."""
        url = f"{self._base}/{container_id}"
        params = {"fields": "status_code", "access_token": self._token}

        for attempt in range(max_polls):
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            status = resp.json().get("status_code", "")

            if status == "FINISHED":
                logger.debug("Container %s ready after %d poll(s).", container_id, attempt + 1)
                return
            if status == "ERROR":
                raise RuntimeError(f"Container {container_id} failed with status ERROR.")

            logger.debug("Container %s status: %s. Waiting 5s...", container_id, status)
            time.sleep(5)

        raise TimeoutError(f"Container {container_id} did not become ready in time.")

    def _publish_container(self, container_id: str) -> str:
        url = f"{self._base}/{self._account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self._token,
        }
        return self._post(url, payload)["id"]

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
