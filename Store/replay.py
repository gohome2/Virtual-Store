"""Export the completed baseline and PPO evaluation logs for the Canvas replay."""

import csv
import json
import math
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from config import (
    CLOSING_HOUR,
    DATA_DIR,
    EPISODE_DAYS,
    EVALUATION_RUNS,
    OPENING_HOUR,
    PUBLIC_DIR,
    RESULTS_DIR,
)
from env import ACTION_NAMES, COUPON, FULL_PRICE_CONTRIBUTION_KRW, RAIN_THRESHOLD_MM

PROJECT_NAME = "Yeouido Riverside Café"
OLDER_ADULT_AGE = 65
OFFICE_TERMS = ("사무", "비서", "회계", "경리", "행정", "금융", "보험", "조사")
LEISURE_TERMS = ("산책", "조깅", "자전거", "한강", "공원", "등산", "트레킹")
RECORDS = (
    ("nothing", "Do nothing", "do_nothing.csv"),
    ("coupon", "Daily coupons", "always_coupon.csv"),
    ("random", "Random outreach", "random_outreach.csv"),
    ("selective", "Selective weekly outreach", "selective_outreach.csv"),
    ("ppo_v1", "Trained policy PPO v1", "ppo_v1.csv"),
)
REQUIRED_LOG_COLUMNS = {"date", "target", "action", "reaction", "profit"}
REQUIRED_PERSONA_COLUMNS = {"customer_id", "age", "occupation", "hobbies_and_interests"}


def _check_columns(reader, required, path):
    missing = required.difference(reader.fieldnames or ())
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")


def _style(occupation, hobbies):
    if any(term in occupation for term in OFFICE_TERMS):
        return "office"
    if any(term in hobbies for term in LEISURE_TERMS):
        return "leisure"
    return "resident"


def _load_personas(path):
    personas = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        _check_columns(reader, REQUIRED_PERSONA_COLUMNS, path)
        for row in reader:
            try:
                customer_id = int(row["customer_id"])
                age = int(row["age"])
                if customer_id <= 0 or customer_id in personas:
                    raise ValueError(f"Invalid or duplicate customer ID: {customer_id}")
                if age < 19:
                    raise ValueError(f"Invalid adult age: {age}")
                personas[customer_id] = {
                    "customer_id": customer_id,
                    "age_group": "older" if age >= OLDER_ADULT_AGE else "adult",
                    "style": _style(row["occupation"], row["hobbies_and_interests"]),
                    "appearance": customer_id,
                }
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path}:{reader.line_num}: {error}") from error
    if not personas:
        raise ValueError(f"{path} contains no customer personas")
    return personas


def _boolean(reaction, key):
    value = reaction[key]
    if type(value) is not bool:
        raise ValueError(f"{key} must be a JSON boolean")
    return value


def _number(reaction, key):
    value = reaction[key]
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{key} must be a finite JSON number")
    return value


def _episode_dates(start_date):
    return [
        (start_date + timedelta(days=offset)).isoformat() for offset in range(EPISODE_DAYS)
    ]


def _accumulate_step(row, customers, days, seen):
    target = int(row["target"])
    calendar_date = row["date"]
    action = int(row["action"])
    if calendar_date not in days:
        raise ValueError(f"Date {calendar_date} is outside the configured evaluation windows")
    if target not in customers:
        raise ValueError(f"Unknown customer ID: {target}")
    if target in seen[calendar_date]:
        raise ValueError(f"Duplicate customer {target} on {calendar_date}")
    if not 0 <= action < len(ACTION_NAMES):
        raise ValueError(f"Invalid executed action: {action}")

    reaction = json.loads(row["reaction"])
    weather = {
        "rainfall_mm": _number(reaction, "rainfall_mm"),
        "is_public_holiday": _boolean(reaction, "is_public_holiday"),
        "is_weekend": _boolean(reaction, "is_weekend"),
    }
    if weather["rainfall_mm"] < 0:
        raise ValueError("rainfall_mm cannot be negative")

    day = days[calendar_date]
    if day is None:
        day = {
            "date": calendar_date,
            **weather,
            "rainy": weather["rainfall_mm"] >= RAIN_THRESHOLD_MM,
            "profit_krw": 0,
            "reward": 0.0,
            "opt_outs": 0,
            "visitors": [],
        }
        days[calendar_date] = day
    elif any(day[key] != value for key, value in weather.items()):
        raise ValueError(f"Conflicting weather or calendar data on {calendar_date}")

    day["profit_krw"] += int(row["profit"])
    day["reward"] += _number(reaction, "reward")
    day["opt_outs"] += int(_boolean(reaction, "opted_out_today"))
    visited = _boolean(reaction, "visited")
    redeemed = _boolean(reaction, "redeemed_coupon")
    if redeemed and (not visited or action != COUPON):
        raise ValueError("A redeemed coupon requires a recorded visit and executed coupon action")
    if visited:
        day["visitors"].append(
            {"customer_id": target, "action": action, "redeemed_coupon": redeemed}
        )
    seen[calendar_date].add(target)


def _record(path, customers, key, label):
    windows = [
        (start.isoformat(), seed, _episode_dates(start)) for start, seed in EVALUATION_RUNS
    ]
    days = {calendar_date: None for _, _, dates in windows for calendar_date in dates}
    seen = {calendar_date: set() for calendar_date in days}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        _check_columns(reader, REQUIRED_LOG_COLUMNS, path)
        for row in reader:
            try:
                _accumulate_step(row, customers, days, seen)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{path}:{reader.line_num}: {error}") from error

    for calendar_date, customer_ids in seen.items():
        if customer_ids != customers:
            raise ValueError(
                f"{path} has {len(customer_ids)} of {len(customers)} expected "
                f"customers on {calendar_date}"
            )
        days[calendar_date]["visitors"].sort(key=lambda visitor: visitor["customer_id"])
    if key == "ppo_v1":
        reward_label = f"Daily contribution profit ÷ {FULL_PRICE_CONTRIBUTION_KRW:,}"
    else:
        reward_label = "Daily contribution profit in KRW"
    return {
        "key": key,
        "label": label,
        "reward_label": reward_label,
        "episodes": [
            {"start_date": start, "seed": seed, "days": [days[day] for day in dates]}
            for start, seed, dates in windows
        ],
    }


def export_replay(
    logs_dir: Path = RESULTS_DIR / "logs",
    personas_path: Path = DATA_DIR / "personas.csv",
    output_dir: Path = PUBLIC_DIR / "data",
) -> int:
    """Write the replay and minimal persona JSON files. Return the record count."""
    personas = _load_personas(personas_path)
    customers = set(personas)
    records = []
    for key, label, filename in RECORDS:
        path = logs_dir / filename
        if key == "ppo_v1" and not path.exists():
            continue
        records.append(_record(path, customers, key, label))

    replay = {
        "project": {
            "name": PROJECT_NAME,
            "opening_hour": OPENING_HOUR,
            "closing_hour": CLOSING_HOUR,
            "episode_days": EPISODE_DAYS,
            "rain_threshold_mm": RAIN_THRESHOLD_MM,
        },
        "records": records,
    }
    payloads = {
        "replays.json": replay,
        "personas.json": [personas[customer_id] for customer_id in sorted(personas)],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as scratch:
        for name, payload in payloads.items():
            content = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            (Path(scratch) / name).write_text(content + "\n", encoding="utf-8")
        for name in payloads:
            (Path(scratch) / name).replace(output_dir / name)
    return len(records)


if __name__ == "__main__":
    print(f"Exported {export_replay()} replay records to {PUBLIC_DIR / 'data'}")
