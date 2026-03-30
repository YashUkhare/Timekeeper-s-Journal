"""
caption_card_generator.py
─────────────────────────
Renders a styled 1080×1920 caption card whose colour palette and mood
are derived from the story's Style and Mood columns.
"""
import logging
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import GENERATED_IMAGES_DIR

logger = logging.getLogger("instagram_bot.caption_card_generator")

CARD_W, CARD_H = 1080, 1920
PADDING = 90


# ── Theme definitions ──────────────────────────────────────────────────────────
# Each theme defines: bg_top, bg_bottom, accent, title_col, body_col,
#                     teaser_bg, teaser_col, divider_col, line_col
THEMES = {
    # Warm / golden themes
    "cinematic": {
        "bg_top": (12, 8, 4), "bg_bottom": (35, 20, 8),
        "accent": (200, 150, 60), "title": (255, 235, 180),
        "body": (220, 205, 170), "teaser_bg": (45, 28, 8),
        "teaser": (200, 150, 60), "divider": (80, 55, 20),
    },
    "steampunk": {
        "bg_top": (18, 10, 4), "bg_bottom": (45, 25, 5),
        "accent": (180, 110, 40), "title": (255, 220, 150),
        "body": (210, 185, 140), "teaser_bg": (50, 30, 8),
        "teaser": (220, 140, 50), "divider": (90, 60, 20),
    },
    # Cold / blue themes
    "noir": {
        "bg_top": (4, 4, 10), "bg_bottom": (8, 8, 25),
        "accent": (100, 130, 200), "title": (210, 220, 255),
        "body": (175, 185, 220), "teaser_bg": (12, 12, 35),
        "teaser": (120, 155, 220), "divider": (40, 45, 90),
    },
    "sci-fi": {
        "bg_top": (2, 8, 18), "bg_bottom": (5, 20, 40),
        "accent": (0, 200, 220), "title": (180, 240, 255),
        "body": (150, 210, 230), "teaser_bg": (4, 22, 44),
        "teaser": (0, 190, 210), "divider": (10, 70, 90),
    },
    # Purple / mystical themes
    "fantasy": {
        "bg_top": (8, 4, 18), "bg_bottom": (22, 8, 45),
        "accent": (170, 100, 255), "title": (230, 210, 255),
        "body": (195, 175, 230), "teaser_bg": (28, 10, 55),
        "teaser": (160, 90, 240), "divider": (65, 35, 110),
    },
    "surrealist": {
        "bg_top": (10, 4, 22), "bg_bottom": (28, 8, 50),
        "accent": (200, 80, 220), "title": (240, 200, 255),
        "body": (200, 170, 230), "teaser_bg": (32, 8, 55),
        "teaser": (190, 70, 210), "divider": (80, 25, 100),
    },
    # Dark / gritty
    "war": {
        "bg_top": (6, 6, 6), "bg_bottom": (20, 14, 10),
        "accent": (180, 60, 50), "title": (230, 210, 200),
        "body": (200, 185, 175), "teaser_bg": (28, 16, 12),
        "teaser": (190, 70, 60), "divider": (70, 40, 35),
    },
    "apocalyptic": {
        "bg_top": (10, 5, 2), "bg_bottom": (30, 12, 4),
        "accent": (210, 80, 20), "title": (255, 210, 170),
        "body": (220, 190, 155), "teaser_bg": (38, 14, 4),
        "teaser": (220, 90, 25), "divider": (85, 40, 15),
    },
    # Warm nostalgic
    "vintage": {
        "bg_top": (16, 12, 6), "bg_bottom": (38, 28, 14),
        "accent": (190, 155, 80), "title": (245, 230, 190),
        "body": (215, 200, 165), "teaser_bg": (44, 32, 14),
        "teaser": (185, 148, 75), "divider": (85, 65, 28),
    },
    # Default fallback
    "default": {
        "bg_top": (8, 8, 16), "bg_bottom": (20, 16, 35),
        "accent": (140, 120, 200), "title": (230, 225, 250),
        "body": (195, 188, 225), "teaser_bg": (25, 18, 45),
        "teaser": (140, 115, 200), "divider": (55, 45, 90),
    },
}

MOOD_THEME_MAP = {
    "mysterious": "fantasy",   "mystery": "fantasy",
    "tense":      "noir",      "dark":    "noir",
    "suspense":   "noir",      "thriller":"noir",
    "magical":    "fantasy",   "mystical":"surrealist",
    "sci-fi":     "sci-fi",    "futuristic":"sci-fi",
    "cinematic":  "cinematic", "epic":    "cinematic",
    "war":        "war",       "battle":  "war",
    "vintage":    "vintage",   "nostalgic":"vintage",
    "steampunk":  "steampunk",
    "hopeful":    "cinematic", "warm":    "vintage",
    "chaos":      "apocalyptic","apocalyptic":"apocalyptic",
    "surreal":    "surrealist",
}

STYLE_THEME_MAP = {
    "cinematic realism":       "cinematic",
    "dark fantasy art":        "fantasy",
    "steampunk illustration":  "steampunk",
    "vintage photography":     "vintage",
    "painterly impressionism": "vintage",
    "sci-fi concept art":      "sci-fi",
    "noir aesthetic":          "noir",
    "epic adventure art":      "cinematic",
    "documentary realism":     "noir",
    "surrealist digital art":  "surrealist",
}


def _pick_theme(style: str, mood: str) -> dict:
    s, m = style.lower(), mood.lower()
    # Try exact style match first
    for key, theme in STYLE_THEME_MAP.items():
        if key in s:
            return THEMES[theme]
    # Then mood keywords
    for key, theme in MOOD_THEME_MAP.items():
        if key in m:
            return THEMES[theme]
    return THEMES["default"]


def _gradient(draw: ImageDraw.ImageDraw, top: tuple, bottom: tuple) -> None:
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    ]
    for p in (bold_paths if bold else regular_paths):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.ImageFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
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


def _draw_text_block(
    draw, lines: list[str], font, color: tuple, x: int, y: int, line_h: int
) -> int:
    """Draw lines of text, return new y position."""
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_h
    return y


def strip_emojis(text: str) -> str:
    return "".join(
        ch for ch in text
        if not unicodedata.category(ch).startswith("So")
        and not (0x1F300 <= ord(ch) <= 0x1FAFF)
        and not (0x2600  <= ord(ch) <= 0x27BF)
    ).strip()


class CaptionCardGenerator:

    def generate(
        self,
        caption: str,
        day: int,
        title: str,
        style: str = "",
        mood: str = "",
    ) -> Path:
        logger.info("Generating caption card for Day %d | style='%s' mood='%s'", day, style, mood)

        theme = _pick_theme(style, mood)

        # ── Parse caption sections ─────────────────────────────────────────
        # Expected: body \n\n teaser \n\n hashtags
        parts = [p.strip() for p in caption.strip().split("\n\n") if p.strip()]
        body    = strip_emojis(parts[0]) if len(parts) > 0 else ""
        teaser  = strip_emojis(parts[1]) if len(parts) > 1 else ""
        # parts[2] = hashtags — intentionally omitted from card

        # Strip leading "Tomorrow:" prefix if Gemini included it
        teaser = re.sub(r"^(tomorrow\s*:?\s*)", "", teaser, flags=re.IGNORECASE).strip()

        # ── Canvas ────────────────────────────────────────────────────────
        img  = Image.new("RGB", (CARD_W, CARD_H))
        draw = ImageDraw.Draw(img)
        _gradient(draw, theme["bg_top"], theme["bg_bottom"])

        # ── Top accent bar ────────────────────────────────────────────────
        draw.rectangle([(0, 0), (CARD_W, 10)], fill=theme["accent"])

        # ── Subtle texture lines (horizontal, very faint) ─────────────────
        for yy in range(60, CARD_H - 60, 120):
            a = theme["divider"]
            draw.line([(PADDING, yy), (CARD_W - PADDING, yy)], fill=(*a, 40), width=1)

        # ── DAY label ─────────────────────────────────────────────────────
        day_font  = _font(36, bold=True)
        day_text  = f"DAY  {day:03d}"
        day_y     = 70
        draw.text((PADDING, day_y), day_text, font=day_font, fill=theme["accent"])

        # ── Accent divider under DAY ──────────────────────────────────────
        div1_y = day_y + 52
        draw.rectangle(
            [(PADDING, div1_y), (PADDING + 120, div1_y + 3)],
            fill=theme["accent"],
        )

        # ── Title ─────────────────────────────────────────────────────────
        title_font  = _font(78, bold=True)
        title_clean = strip_emojis(title.upper())
        title_lines = _wrap(title_clean, title_font, CARD_W - PADDING * 2, draw)
        title_y     = div1_y + 36
        title_y     = _draw_text_block(draw, title_lines, title_font, theme["title"], PADDING, title_y, 95)

        # ── Full-width divider ────────────────────────────────────────────
        div2_y = title_y + 40
        draw.rectangle(
            [(PADDING, div2_y), (CARD_W - PADDING, div2_y + 2)],
            fill=theme["divider"],
        )

        # ── Story body ────────────────────────────────────────────────────
        body_font  = _font(50)
        body_lines = _wrap(body, body_font, CARD_W - PADDING * 2, draw)
        body_y     = div2_y + 55
        body_y     = _draw_text_block(draw, body_lines, body_font, theme["body"], PADDING, body_y, 70)

        # ── Teaser block ──────────────────────────────────────────────────
        if teaser:
            teaser_font  = _font(44)
            teaser_lines = _wrap(teaser, teaser_font, CARD_W - PADDING * 2 - 40, draw)
            block_h      = len(teaser_lines) * 62 + 50
            teaser_box_y = body_y + 70

            # Rounded background box
            draw.rounded_rectangle(
                [(PADDING, teaser_box_y),
                 (CARD_W - PADDING, teaser_box_y + block_h)],
                radius=18,
                fill=theme["teaser_bg"],
            )
            # Left accent stripe
            draw.rounded_rectangle(
                [(PADDING, teaser_box_y),
                 (PADDING + 6, teaser_box_y + block_h)],
                radius=4,
                fill=theme["accent"],
            )

            # "TOMORROW" label
            label_font = _font(28, bold=True)
            draw.text(
                (PADDING + 28, teaser_box_y + 18),
                "TOMORROW",
                font=label_font,
                fill=theme["accent"],
            )
            # Teaser text
            t_y = teaser_box_y + 52
            _draw_text_block(draw, teaser_lines, teaser_font, theme["teaser"], PADDING + 28, t_y, 62)

        # ── Bottom accent bar ─────────────────────────────────────────────
        draw.rectangle([(0, CARD_H - 10), (CARD_W, CARD_H)], fill=theme["accent"])

        # ── Save ──────────────────────────────────────────────────────────
        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = GENERATED_IMAGES_DIR / f"day_{day:03d}_caption.png"
        img.save(str(file_path), "PNG")

        logger.info("Caption card saved → %s", file_path)
        return file_path
