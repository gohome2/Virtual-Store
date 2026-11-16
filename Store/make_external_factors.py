"""Build the local rainfall and Korean holiday table from public sources."""

import csv
import math
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import holidays
import openmeteo_requests

from config import DATA_DIR, EVALUATION_END, TRAIN_START

# Approximate coordinates of Yeouido Hangang Park, where the virtual café sits.
LATITUDE = 37.527
LONGITUDE = 126.935
LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def main():
    response, = openmeteo_requests.Client().weather_api(
        ARCHIVE_URL,
        params={
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": TRAIN_START.isoformat(),
            "end_date": EVALUATION_END.isoformat(),
            "daily": "rain_sum",
            "timezone": LOCAL_TIMEZONE.key,
            "models": "era5",
        },
    )
    daily = response.Daily()
    timestamps = range(daily.Time(), daily.TimeEnd(), daily.Interval())
    dates = [datetime.fromtimestamp(timestamp, LOCAL_TIMEZONE).date() for timestamp in timestamps]
    expected_dates = [
        TRAIN_START + timedelta(days=offset)
        for offset in range((EVALUATION_END - TRAIN_START).days + 1)
    ]
    if dates != expected_dates:
        raise ValueError("Open-Meteo did not return every expected Seoul calendar date.")

    rainfall = daily.Variables(0).ValuesAsNumpy()
    if len(rainfall) != len(dates) or any(not math.isfinite(value) or value < 0 for value in rainfall):
        raise ValueError("Open-Meteo returned missing or invalid rainfall measurements.")
    public_holidays = holidays.country_holidays("KR", years=range(TRAIN_START.year, EVALUATION_END.year + 1))

    DATA_DIR.mkdir(exist_ok=True)
    output = DATA_DIR / "external_factors.csv"
    with NamedTemporaryFile(mode="w", dir=DATA_DIR, encoding="utf-8", newline="", delete=False) as stream:
        temporary_path = DATA_DIR / stream.name
        try:
            writer = csv.writer(stream)
            writer.writerow(["date", "rainfall_mm", "is_weekend", "is_public_holiday"])
            for day, rain in zip(dates, rainfall, strict=True):
                writer.writerow([day.isoformat(), f"{rain:.3f}", int(day.weekday() >= 5), int(day in public_holidays)])
            stream.flush()
            temporary_path.replace(output)
        finally:
            temporary_path.unlink(missing_ok=True)
    print(f"Saved {len(dates)} daily rows to {output.relative_to(DATA_DIR.parent)}.")


if __name__ == "__main__":
    main()
