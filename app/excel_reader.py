import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger("instagram_bot.excel_reader")

# Excel column names (must match the spreadsheet exactly)
COL_DAY = "Day"
COL_TITLE = "Title"
COL_STORY_PHASE = "Story Phase"
COL_IMAGE_PROMPT = "Image Prompt"
COL_CAPTION_CONTEXT = "Caption Context"
COL_NEXT_DAY_TEASER = "Next Day Teaser"
COL_STYLE = "Style"
COL_MOOD = "Mood"
COL_HASHTAGS = "Hashtags"
COL_STATUS = "Status"

STATUS_PENDING = "Pending"
STATUS_POSTED = "Posted"
STATUS_FAILED = "Failed"


@dataclass
class StoryRow:
    index: int          # DataFrame row index (for updating)
    day: int
    title: str
    story_phase: str
    image_prompt: str
    caption_context: str
    next_day_teaser: str
    style: str
    mood: str
    hashtags: str


class ExcelReader:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    # ──────────────────────────────────────────────────────────────────────────
    def get_today_story(self) -> StoryRow | None:
        """Return the first row whose Status is 'Pending', or None."""
        df = self._load()
        pending = df[df[COL_STATUS].str.strip().str.lower() == STATUS_PENDING.lower()]

        if pending.empty:
            logger.warning("No pending rows found in Excel file.")
            return None

        row = pending.iloc[0]
        idx = pending.index[0]

        logger.info("Found pending row: Day=%s, Title='%s'", row[COL_DAY], row[COL_TITLE])

        return StoryRow(
            index=int(idx),
            day=int(row[COL_DAY]),
            title=str(row[COL_TITLE]).strip(),
            story_phase=str(row[COL_STORY_PHASE]).strip(),
            image_prompt=str(row[COL_IMAGE_PROMPT]).strip(),
            caption_context=str(row[COL_CAPTION_CONTEXT]).strip(),
            next_day_teaser=str(row[COL_NEXT_DAY_TEASER]).strip(),
            style=str(row[COL_STYLE]).strip(),
            mood=str(row[COL_MOOD]).strip(),
            hashtags=str(row[COL_HASHTAGS]).strip(),
        )

    # ──────────────────────────────────────────────────────────────────────────
    def mark_posted(self, row_index: int) -> None:
        """Set Status = 'Posted' for the given DataFrame index."""
        self._update_status(row_index, STATUS_POSTED)

    def mark_failed(self, row_index: int) -> None:
        """Set Status = 'Failed' for the given DataFrame index."""
        self._update_status(row_index, STATUS_FAILED)

    # ──────────────────────────────────────────────────────────────────────────
    def _load(self) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")
        df = pd.read_excel(self.file_path, engine="openpyxl")
        self._validate_columns(df)
        return df

    def _validate_columns(self, df: pd.DataFrame) -> None:
        required = [
            COL_DAY, COL_TITLE, COL_STORY_PHASE, COL_IMAGE_PROMPT,
            COL_CAPTION_CONTEXT, COL_NEXT_DAY_TEASER, COL_STYLE,
            COL_MOOD, COL_HASHTAGS, COL_STATUS,
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Excel file is missing columns: {missing}")

    def _update_status(self, row_index: int, status: str) -> None:
        df = self._load()
        df.at[row_index, COL_STATUS] = status
        df.to_excel(self.file_path, index=False, engine="openpyxl")
        logger.info("Row %d status updated to '%s'.", row_index, status)
