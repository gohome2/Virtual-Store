"""Fixed periods and paths for the café simulation."""

from datetime import date, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
RESULTS_DIR = PROJECT_DIR / "results"
PUBLIC_DIR = PROJECT_DIR / "public"

EPISODE_DAYS = 30
TRAIN_START = date(2016, 1, 1)
TRAIN_END = date(2024, 12, 31)
EVALUATION_START = date(2025, 1, 1)
EVALUATION_END = date(2025, 12, 31)
MAX_OPT_OUT_SHARE = 0.05
OPENING_HOUR = 10
CLOSING_HOUR = 22

evaluation_days = (EVALUATION_END - EVALUATION_START).days + 1
evaluation_starts = (
    EVALUATION_START + timedelta(days=offset)
    for offset in range(0, evaluation_days - EPISODE_DAYS + 1, EPISODE_DAYS)
)
EVALUATION_RUNS = tuple((start, int(start.strftime("%Y%m%d"))) for start in evaluation_starts)
