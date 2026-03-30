import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import GENERATED_IMAGES_DIR

logger = logging.getLogger("instagram_bot.caption_card_generator")

# Card dimensions — 1080x1920 (9:16 Instagram Story / Carousel)
CARD_W = 1080
CARD_H = 1920

# Colour palette
BG_TOP       = (10, 10, 30)      # deep navy
BG_BOTTOM    = (30, 10, 50)      # dark violet
ACCENT       = (180, 130, 255)   # soft purple
TEXT_MAIN    = (240, 235, 255)   # near-white
TEXT_MUTED   = (160, 150, 190)   # muted lavender
DIVIDER      = (80, 60, 120)     # dim purple


def _gradient_background(draw: ImageDraw.ImageDraw) -> None:
    """Paint a vertical gradient from BG_TOP to BG_BOTTOM."""
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))


def _load_font(size: int) -> ImageFont.ImageFont:
    """Try to load DejaVu (available on Ubuntu runners), fallback to default."""
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ]
    for path in font_candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _load_font_regular(size: int) -> ImageFont.ImageFont:
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    ]
    for path in font_candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class CaptionCardGenerator:
    def generate(self, caption: str, day: int, title: str) -> Path:
        """
        Render a styled caption card image and save it.
        Returns the local file path.
        """
        logger.info("Generating caption card for Day %d", day)

        img = Image.new("RGB", (CARD_W, CARD_H))
        draw = ImageDraw.Draw(img)

        # ── Background ─────────────────────────────────────────────────────
        _gradient_background(draw)

        # ── Decorative top bar ──────────────────────────────────────────────
        draw.rectangle([(0, 0), (CARD_W, 8)], fill=ACCENT)

        # ── DAY badge ───────────────────────────────────────────────────────
        badge_font = _load_font(42)
        badge_text = f"DAY {day:03d}"
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 20
        bx, by = 80, 100
        draw.rounded_rectangle(
            [(bx - pad, by - pad), (bx + bw + pad, by + bh + pad)],
            radius=16,
            fill=ACCENT,
        )
        draw.text((bx, by), badge_text, font=badge_font, fill=(10, 10, 30))

        # ── Title ───────────────────────────────────────────────────────────
        title_font = _load_font(72)
        title_y = by + bh + pad * 3 + 20
        title_lines = _wrap_text(title.upper(), title_font, CARD_W - 160, draw)
        for line in title_lines:
            draw.text((80, title_y), line, font=title_font, fill=TEXT_MAIN)
            title_y += 90

        # ── Divider ─────────────────────────────────────────────────────────
        div_y = title_y + 30
        draw.rectangle([(80, div_y), (CARD_W - 80, div_y + 3)], fill=DIVIDER)

        # ── Parse caption into story body / teaser / hashtags ───────────────
        parts = caption.strip().split("\n\n")
        story_body = parts[0] if len(parts) > 0 else ""
        teaser     = parts[1] if len(parts) > 1 else ""
        hashtags   = parts[2] if len(parts) > 2 else ""

        # ── Story body ──────────────────────────────────────────────────────
        body_font = _load_font_regular(52)
        body_y = div_y + 50
        body_lines = _wrap_text(story_body, body_font, CARD_W - 160, draw)
        for line in body_lines:
            draw.text((80, body_y), line, font=body_font, fill=TEXT_MAIN)
            body_y += 72

        # ── Teaser block ────────────────────────────────────────────────────
        if teaser:
            teaser_y = body_y + 60
            draw.rectangle(
                [(60, teaser_y - 20), (CARD_W - 60, teaser_y + 130)],
                fill=(40, 20, 70),
            )
            teaser_font = _load_font_regular(44)
            teaser_lines = _wrap_text(teaser, teaser_font, CARD_W - 200, draw)
            for line in teaser_lines:
                draw.text((90, teaser_y), line, font=teaser_font, fill=ACCENT)
                teaser_y += 60

        # ── Hashtags ────────────────────────────────────────────────────────
        if hashtags:
            tag_font = _load_font_regular(36)
            tag_lines = _wrap_text(hashtags, tag_font, CARD_W - 160, draw)
            tag_y = CARD_H - (len(tag_lines) * 48) - 80
            for line in tag_lines:
                draw.text((80, tag_y), line, font=tag_font, fill=TEXT_MUTED)
                tag_y += 48

        # ── Decorative bottom bar ───────────────────────────────────────────
        draw.rectangle([(0, CARD_H - 8), (CARD_W, CARD_H)], fill=ACCENT)

        # ── Save ────────────────────────────────────────────────────────────
        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}_caption.png"
        img.save(str(file_path), "PNG")

        logger.info("Caption card saved → %s", file_path)
        return file_path
