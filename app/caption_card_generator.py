"""
caption_card_generator.py
─────────────────────────
Overlays story text onto card_template.png using exact pixel zones
provided by the user. Fonts are loaded from data/fonts/.
"""
import logging
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import BASE_DIR, GENERATED_IMAGES_DIR

logger = logging.getLogger("instagram_bot.caption_card_generator")

# ── Asset paths ────────────────────────────────────────────────────────────────
TEMPLATE_PATH  = BASE_DIR / "data" / "card_template.png"
FONTS_DIR      = BASE_DIR / "data" / "fonts"

FONT_CINZEL        = FONTS_DIR / "Cinzel-Regular.ttf"
FONT_UNIFRAKTUR    = FONTS_DIR / "UnifrakturMaguntia-Book.ttf"
FONT_IMFELL        = FONTS_DIR / "IMFellEnglishSC-Regular.ttf"

# ── Text zone coordinates (x1, y1, x2, y2) ────────────────────────────────────
ZONE_DAY    = (308,  93,  490,  123)   # Day number bar
ZONE_TITLE  = (225, 133,  550,  207)   # Title area
ZONE_BODY   = (154, 252,  633,  710)   # Story body
ZONE_TEASER = (215, 760,  570,  805)   # Next day teaser

# ── Colours ────────────────────────────────────────────────────────────────────
COLOR_DAY    = (205, 170,  85)   # Burnished brass
COLOR_TITLE  = (175, 138,  48)   # Deep etched gold
COLOR_BODY   = (210, 190, 130)   # Warm parchment gold
COLOR_TEASER = (195, 125,  65)   # Copper-brass
COLOR_SHADOW = (  0,   0,   0,  160)  # Drop shadow (RGBA)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _strip_emojis(text: str) -> str:
    return "".join(
        ch for ch in text
        if not unicodedata.category(ch).startswith("So")
        and not (0x1F300 <= ord(ch) <= 0x1FAFF)
        and not (0x2600  <= ord(ch) <= 0x27BF)
    ).strip()


def _load_font(path: Path, size: int) -> ImageFont.ImageFont:
    """Load font from repo; fall back to DejaVu then default."""
    if path.exists():
        return ImageFont.truetype(str(path), size)
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ]
    for fb in fallbacks:
        if Path(fb).exists():
            logger.warning("Font %s not found, falling back to %s", path.name, fb)
            return ImageFont.truetype(fb, size)
    return ImageFont.load_default()


def _wrap_text(
    text: str,
    font: ImageFont.ImageFont,
    max_w: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """Word-wrap text to fit within max_w pixels."""
    words  = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _autofit_font(
    path: Path,
    text: str,
    zone_w: int,
    zone_h: int,
    draw: ImageDraw.ImageDraw,
    max_size: int,
    min_size: int = 8,
    allow_wrap: bool = False,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    """
    Find the largest font size where text fits inside zone_w x zone_h.
    Returns (font, lines, line_height).
    """
    for size in range(max_size, min_size - 1, -1):
        font = _load_font(path, size)
        lh   = draw.textbbox((0, 0), "Ag", font=font)[3] + 4

        if allow_wrap:
            lines = _wrap_text(text, font, zone_w, draw)
        else:
            lines = [text]

        total_h = len(lines) * lh
        max_line_w = max(draw.textbbox((0, 0), l, font=font)[2] for l in lines)

        if total_h <= zone_h and max_line_w <= zone_w:
            return font, lines, lh

    # Minimum size fallback — wrap and clip
    font  = _load_font(path, min_size)
    lh    = draw.textbbox((0, 0), "Ag", font=font)[3] + 4
    lines = _wrap_text(text, font, zone_w, draw) if allow_wrap else [text]
    return font, lines, lh


def _draw_text_in_zone(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    line_h: int,
    zone: tuple[int, int, int, int],
    color: tuple,
    align: str = "center",   # "center" | "left"
    valign: str = "center",  # "center" | "top"
    shadow: bool = True,
) -> None:
    x1, y1, x2, y2 = zone
    zone_w = x2 - x1
    zone_h = y2 - y1
    total_text_h = len(lines) * line_h

    # Vertical position
    if valign == "center":
        start_y = y1 + (zone_h - total_text_h) // 2
    else:
        start_y = y1

    for i, line in enumerate(lines):
        text_w = draw.textbbox((0, 0), line, font=font)[2]
        if align == "center":
            start_x = x1 + (zone_w - text_w) // 2
        else:
            start_x = x1

        # Drop shadow for legibility
        if shadow:
            draw.text((start_x + 2, start_y + 2), line, font=font, fill=(0, 0, 0, 180))

        draw.text((start_x, start_y), line, font=font, fill=color)
        start_y += line_h


# ── Main class ─────────────────────────────────────────────────────────────────

class CaptionCardGenerator:

    def generate(
        self,
        caption: str,
        day: int,
        title: str,
        style: str = "",
        mood: str = "",
    ) -> Path:
        logger.info("Generating caption card for Day %d", day)

        if not TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

        # ── Load template ──────────────────────────────────────────────────
        img  = Image.open(TEMPLATE_PATH).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # ── Parse caption sections ─────────────────────────────────────────
        parts   = [p.strip() for p in caption.strip().split("\n\n") if p.strip()]
        body    = _strip_emojis(parts[0]) if len(parts) > 0 else ""
        teaser  = _strip_emojis(parts[1]) if len(parts) > 1 else ""
        # parts[2] = hashtags — NOT rendered on card

        # Clean "Tomorrow:" prefix from teaser if Gemini included it
        teaser = re.sub(r"^(tomorrow\s*[:\-]?\s*)", "", teaser, flags=re.IGNORECASE).strip()

        title_clean = _strip_emojis(title.upper())
        day_text    = f"DAY  {day:03d}"

        # ── Zone dimensions ────────────────────────────────────────────────
        def zone_dims(z):
            return z[2] - z[0], z[3] - z[1]   # w, h

        # ── 1. DAY NUMBER ──────────────────────────────────────────────────
        dw, dh = zone_dims(ZONE_DAY)
        day_font, day_lines, day_lh = _autofit_font(
            FONT_CINZEL, day_text, dw, dh, draw,
            max_size=26, allow_wrap=False,
        )
        _draw_text_in_zone(
            draw, day_lines, day_font, day_lh,
            ZONE_DAY, COLOR_DAY, align="center", valign="center",
        )

        # ── 2. TITLE ───────────────────────────────────────────────────────
        tw, th = zone_dims(ZONE_TITLE)
        title_font, title_lines, title_lh = _autofit_font(
            FONT_UNIFRAKTUR, title_clean, tw, th, draw,
            max_size=42, allow_wrap=True,
        )
        _draw_text_in_zone(
            draw, title_lines, title_font, title_lh,
            ZONE_TITLE, COLOR_TITLE, align="center", valign="center",
        )

        # ── 3. STORY BODY ──────────────────────────────────────────────────
        bw, bh = zone_dims(ZONE_BODY)
        body_font, body_lines, body_lh = _autofit_font(
            FONT_IMFELL, body, bw, bh, draw,
            max_size=24, allow_wrap=True,
        )
        _draw_text_in_zone(
            draw, body_lines, body_font, body_lh,
            ZONE_BODY, COLOR_BODY, align="left", valign="top",
        )

        # ── 4. TEASER ──────────────────────────────────────────────────────
        if teaser:
            rw, rh = zone_dims(ZONE_TEASER)
            teaser_font, teaser_lines, teaser_lh = _autofit_font(
                FONT_CINZEL, teaser, rw, rh, draw,
                max_size=18, allow_wrap=True,
            )
            _draw_text_in_zone(
                draw, teaser_lines, teaser_font, teaser_lh,
                ZONE_TEASER, COLOR_TEASER, align="center", valign="center",
            )

        # ── Save ───────────────────────────────────────────────────────────
        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}_caption.png"

        # Convert back to RGB for JPEG-compatible upload
        img.convert("RGB").save(str(file_path), "PNG")

        logger.info("Caption card saved → %s", file_path)
        return file_path
