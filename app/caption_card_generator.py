"""
caption_card_generator.py
─────────────────────────
Overlays story text onto card_template.png (1071×1350).
Text zones are auto-detected from the template's clear dark areas.
Fonts loaded from data/fonts/.
"""
import logging
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import BASE_DIR, GENERATED_IMAGES_DIR

logger = logging.getLogger("instagram_bot.caption_card_generator")

# ── Asset paths ────────────────────────────────────────────────────────────────
TEMPLATE_PATH = BASE_DIR / "data" / "card_template.png"
FONTS_DIR     = BASE_DIR / "data" / "fonts"

FONT_CINZEL     = FONTS_DIR / "Cinzel-Regular.ttf"
FONT_UNIFRAKTUR = FONTS_DIR / "UnifrakturMaguntia-Book.ttf"
FONT_IMFELL     = FONTS_DIR / "IMFellEnglishSC-Regular.ttf"

# ── Text zones (x1, y1, x2, y2) — derived from template analysis ──────────────
# Template size: 1071 × 1350
ZONE_DAY    = (380, 160, 690, 208)    # Centred between corner decorations — 310×48px
ZONE_TITLE  = (140, 220, 930, 315)    # Full-width title strip            — 790×95px
ZONE_BODY   = (140, 335, 930, 720)    # Large clear expanse               — 790×385px
ZONE_TEASER = (200, 738, 870, 800)    # Just above the clock              — 670×62px

# ── Colours ────────────────────────────────────────────────────────────────────
COLOR_DAY    = (205, 170,  85)    # Burnished brass
COLOR_TITLE  = (170, 130,  42)    # Deep etched gold
COLOR_BODY   = (215, 195, 140)    # Warm parchment gold
COLOR_TEASER = (195, 125,  65)    # Copper-brass


# ── Helpers ────────────────────────────────────────────────────────────────────

def _strip_emojis(text: str) -> str:
    return "".join(
        ch for ch in text
        if not unicodedata.category(ch).startswith("So")
        and not (0x1F300 <= ord(ch) <= 0x1FAFF)
        and not (0x2600  <= ord(ch) <= 0x27BF)
    ).strip()


def _load_font(path: Path, size: int) -> ImageFont.ImageFont:
    if path.exists():
        return ImageFont.truetype(str(path), size)
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ]
    for fb in fallbacks:
        if Path(fb).exists():
            logger.warning("Font %s not found — falling back to %s", path.name, fb)
            return ImageFont.truetype(fb, size)
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.ImageFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = f"{cur} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _autofit(
    font_path: Path,
    text: str,
    zone: tuple,
    draw: ImageDraw.ImageDraw,
    max_size: int,
    min_size: int = 8,
    wrap: bool = True,
    padding: int = 10,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    """Return (font, lines, line_height) that fit inside zone."""
    x1, y1, x2, y2 = zone
    zone_w = x2 - x1 - padding * 2
    zone_h = y2 - y1 - padding * 2

    for size in range(max_size, min_size - 1, -1):
        font = _load_font(font_path, size)
        lh   = draw.textbbox((0, 0), "Ag", font=font)[3] + 5
        lines = _wrap(text, font, zone_w, draw) if wrap else [text]
        if len(lines) * lh <= zone_h:
            max_w = max(draw.textbbox((0, 0), l, font=font)[2] for l in lines)
            if max_w <= zone_w:
                return font, lines, lh

    font  = _load_font(font_path, min_size)
    lh    = draw.textbbox((0, 0), "Ag", font=font)[3] + 5
    lines = _wrap(text, font, zone_w, draw) if wrap else [text]
    return font, lines, lh


def _place(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    line_h: int,
    zone: tuple,
    color: tuple,
    align: str = "center",   # "center" | "left"
    valign: str = "center",  # "center" | "top"
    padding: int = 10,
) -> None:
    x1, y1, x2, y2 = zone
    zone_w = x2 - x1
    zone_h = y2 - y1
    total_h = len(lines) * line_h

    start_y = y1 + padding + (zone_h - total_h) // 2 if valign == "center" else y1 + padding

    for line in lines:
        text_w = draw.textbbox((0, 0), line, font=font)[2]
        start_x = x1 + (zone_w - text_w) // 2 if align == "center" else x1 + padding

        # Subtle drop shadow for legibility on textured background
        draw.text((start_x + 2, start_y + 2), line, font=font, fill=(0, 0, 0, 200))
        draw.text((start_x,     start_y    ), line, font=font, fill=color)
        start_y += line_h


# ── Main ───────────────────────────────────────────────────────────────────────

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

        # ── Parse caption ──────────────────────────────────────────────────
        parts  = [p.strip() for p in caption.strip().split("\n\n") if p.strip()]
        body   = _strip_emojis(parts[0]) if len(parts) > 0 else ""
        teaser = _strip_emojis(parts[1]) if len(parts) > 1 else ""
        # parts[2] = hashtags — NOT rendered on card

        teaser = re.sub(r"^(tomorrow\s*[:\-]?\s*)", "", teaser, flags=re.IGNORECASE).strip()
        title_clean = _strip_emojis(title.upper())
        day_text    = f"~ DAY  {day:03d} ~"

        # ── 1. DAY NUMBER — Cinzel, centred, brass ─────────────────────────
        day_font, day_lines, day_lh = _autofit(
            FONT_CINZEL, day_text, ZONE_DAY, draw, max_size=28,
        )
        _place(draw, day_lines, day_font, day_lh, ZONE_DAY, COLOR_DAY,
               align="center", valign="center")

        # ── 2. TITLE — UnifrakturMaguntia, centred, deep gold ─────────────
        title_font, title_lines, title_lh = _autofit(
            FONT_CINZEL, title_clean, ZONE_TITLE, draw, max_size=60, wrap=True,
        )
        _place(draw, title_lines, title_font, title_lh, ZONE_TITLE, COLOR_TITLE,
               align="center", valign="center")

        # ── 3. STORY BODY — IM Fell English SC, left-aligned, parchment ───
        body_font, body_lines, body_lh = _autofit(
            FONT_IMFELL, body, ZONE_BODY, draw, max_size=32, wrap=True,
        )
        _place(draw, body_lines, body_font, body_lh, ZONE_BODY, COLOR_BODY,
               align="left", valign="top", padding=14)

        # ── 4. TEASER — Cinzel, centred, copper ───────────────────────────
        if teaser:
            teaser_font, teaser_lines, teaser_lh = _autofit(
                FONT_CINZEL, teaser, ZONE_TEASER, draw, max_size=22, wrap=True,
            )
            _place(draw, teaser_lines, teaser_font, teaser_lh, ZONE_TEASER, COLOR_TEASER,
                   align="center", valign="center")

        # ── Save as RGB PNG ────────────────────────────────────────────────
        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}_caption.png"
        img.convert("RGB").save(str(file_path), "PNG")

        logger.info("Caption card saved → %s  (%dx%d)", file_path, img.width, img.height)
        return file_path
