"""
generate_excel.py
-----------------
Run once to create a sample story.xlsx with 365 days of Time Traveler content.
Usage: python generate_excel.py
"""

from pathlib import Path
import pandas as pd

PHASES = [
    "The Discovery",
    "First Jump",
    "Ancient World",
    "Medieval Ages",
    "Industrial Revolution",
    "World War I",
    "World War II",
    "Cold War Era",
    "The Digital Age",
    "The Return",
]

STYLES = [
    "cinematic realism",
    "dark fantasy art",
    "steampunk illustration",
    "vintage photography style",
    "painterly impressionism",
    "sci-fi concept art",
    "noir aesthetic",
    "epic adventure art",
    "documentary realism",
    "surrealist digital art",
]

MOODS = [
    "mysterious and tense",
    "awe-inspiring and vast",
    "melancholic and nostalgic",
    "thrilling and urgent",
    "serene and magical",
    "dark and foreboding",
    "hopeful and warm",
    "chaotic and overwhelming",
    "calm before the storm",
    "triumphant and emotional",
]


def generate_day(day: int) -> dict:
    phase_idx = (day - 1) % len(PHASES)
    style_idx = (day - 1) % len(STYLES)
    mood_idx = (day - 1) % len(MOODS)

    phase = PHASES[phase_idx]
    style = STYLES[style_idx]
    mood = MOODS[mood_idx]

    return {
        "Day": day,
        "Title": f"Day {day}: {phase}",
        "Story Phase": phase,
        "Image Prompt": (
            f"A time traveler in {phase.lower()}, dramatic scene, "
            f"atmospheric environment with glowing time portal, "
            f"historical details accurate to the era"
        ),
        "Caption Context": (
            f"Day {day} of the time travel saga. Our traveler is deep in the era of {phase.lower()}. "
            f"The weight of history presses down as every choice could alter the future. "
            f"The clock is ticking and the portal will close at dawn."
        ),
        "Next Day Teaser": f"The traveler discovers a secret that changes everything about {PHASES[(phase_idx + 1) % len(PHASES)].lower()}",
        "Style": style,
        "Mood": mood,
        "Hashtags": (
            "#TimeTravel #AIStory #SciFi #TimeLoop #DailyStory "
            "#AIArt #StoryTime #Fiction #Adventure #365DayChallenge"
        ),
        "Status": "Pending",
    }


def main() -> None:
    output_path = Path("data/story.xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [generate_day(day) for day in range(1, 366)]
    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"✅ Created {output_path} with {len(rows)} rows.")


if __name__ == "__main__":
    main()
