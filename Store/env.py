"""Gymnasium environment for one café customer over one outreach episode."""

import csv
import math
from collections.abc import Mapping
from datetime import date, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple

import gymnasium as gym
import numpy as np

from config import EPISODE_DAYS, TRAIN_END, TRAIN_START


ACTION_NAMES = ("nothing", "message", "coupon")
NOTHING, MESSAGE, COUPON = range(len(ACTION_NAMES))
OBSERVATION_FIELDS = (
    "price_sensitivity",
    "fatigue",
    "opted_in",
    "is_weekend",
    "is_public_holiday",
    "days_remaining",
)

# Simulation assumptions from the reaction rules in project_spec.md.
BASE_VISIT_PROBABILITY = 0.08
MESSAGE_VISIT_BONUS = 0.03
COUPON_BASE_BONUS = 0.02
COUPON_SENSITIVITY_BONUS = 0.10
RAIN_THRESHOLD_MM = 5.0
RAIN_MULTIPLIER = 0.75
WEEKEND_MULTIPLIER = 1.25
HOLIDAY_MULTIPLIER = 1.15
FULL_PRICE_CONTRIBUTION_KRW = 4800
COUPON_CONTRIBUTION_KRW = 3600
FATIGUE_CHANGES = (-8, 10, 15)
MAX_FATIGUE = 100
OPT_OUT_FATIGUE = 60
OPT_OUT_PROBABILITY = 0.10

DATA_DIRECTORY = Path(__file__).resolve().parent / "data"
ONE_DAY = timedelta(days=1)


class _Day(NamedTuple):
    rainfall_mm: float
    is_weekend: bool
    is_public_holiday: bool


def _csv_rows(filename):
    with (DATA_DIRECTORY / filename).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(value)


def _flag(value):
    if value not in (0, 1, "0", "1"):
        raise ValueError(f"Expected a calendar flag of 0 or 1, got {value!r}")
    return value in (1, "1")


def _load_customer_traits(source):
    if source is None:
        source = _csv_rows("customer_traits.csv")
    pairs = (
        source.items()
        if isinstance(source, Mapping)
        else ((row["customer_id"], row["price_sensitivity"]) for row in source)
    )
    customers = {}
    for customer_id, sensitivity in pairs:
        customer_id = int(customer_id)
        sensitivity = float(sensitivity)
        if not 0 <= sensitivity <= 1:
            raise ValueError(f"Price sensitivity must be between 0 and 1 for customer {customer_id}")
        if customer_id in customers:
            raise ValueError(f"Duplicate customer ID: {customer_id}")
        customers[customer_id] = sensitivity
    if not customers:
        raise ValueError("At least one customer is required")
    return customers


def _load_external_factors(source):
    if source is None:
        source = _csv_rows("external_factors.csv")
    pairs = (
        source.items()
        if isinstance(source, Mapping)
        else ((row["date"], row) for row in source)
    )
    calendar = {}
    for date_value, row in pairs:
        day = _as_date(date_value)
        rainfall = float(row["rainfall_mm"])
        if not math.isfinite(rainfall) or rainfall < 0:
            raise ValueError(f"Rainfall must be finite and nonnegative for {day}")
        if day in calendar:
            raise ValueError(f"Duplicate external factors date: {day}")
        calendar[day] = _Day(
            rainfall,
            _flag(row["is_weekend"]),
            _flag(row["is_public_holiday"]),
        )
    return calendar


class CafeEnv(gym.Env[np.ndarray, int]):
    """Choose one outreach action each morning for an opted-in customer.

    Test or evaluation callers can inject customer sensitivities as an ID-to-value
    mapping and daily calendar data as a date-to-row mapping. Both inputs also
    accept iterable rows with the same columns as the default CSV files.
    """

    def __init__(self, customer_traits=None, external_factors=None, reward_fn=None):
        super().__init__()
        self.action_space = gym.spaces.Discrete(len(ACTION_NAMES))
        self.observation_space = gym.spaces.Box(
            low=0, high=1, shape=(len(OBSERVATION_FIELDS),), dtype=np.float32
        )
        self._customer_traits = _load_customer_traits(customer_traits)
        self._customer_ids = tuple(sorted(self._customer_traits))
        self._calendar = _load_external_factors(external_factors)
        last_training_start = TRAIN_END - (EPISODE_DAYS - 1) * ONE_DAY
        self._training_starts = tuple(
            day for day in sorted(self._calendar)
            if TRAIN_START <= day <= last_training_start and self._has_episode(day)
        )
        self._reward_fn = reward_fn
        self._day = None

    @property
    def customer_ids(self):
        return self._customer_ids

    @property
    def customer_traits(self):
        return MappingProxyType(self._customer_traits)

    def _has_episode(self, start_date):
        return all(start_date + offset * ONE_DAY in self._calendar for offset in range(EPISODE_DAYS))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        options = {} if options is None else options
        customer_id = options.get("customer_id")
        if customer_id is None:
            customer_id = self._customer_ids[self.np_random.integers(len(self._customer_ids))]
        if customer_id not in self._customer_traits:
            raise ValueError(f"Unknown customer ID: {customer_id}")
        start_date = options.get("start_date")
        if start_date is None:
            if not self._training_starts:
                raise ValueError("External factors do not contain a complete training episode")
            start_date = self._training_starts[self.np_random.integers(len(self._training_starts))]
        else:
            start_date = _as_date(start_date)
            if not self._has_episode(start_date):
                raise ValueError(f"External factors do not cover the episode starting {start_date}")

        self._customer_id = int(customer_id)
        self._price_sensitivity = self._customer_traits[customer_id]
        self._day = start_date
        self._fatigue = 0
        self._opted_in = True
        self._days_remaining = EPISODE_DAYS
        return self._observation(), {"date": self._day.isoformat(), "customer_id": self._customer_id}

    def _observation(self):
        calendar = self._calendar[self._day]
        return np.array(
            [
                self._price_sensitivity,
                self._fatigue / MAX_FATIGUE,
                self._opted_in,
                calendar.is_weekend,
                calendar.is_public_holiday,
                self._days_remaining / EPISODE_DAYS,
            ],
            dtype=np.float32,
        )

    def _visit_probability(self, action, calendar):
        chance = BASE_VISIT_PROBABILITY
        if action == MESSAGE:
            chance += MESSAGE_VISIT_BONUS
        elif action == COUPON:
            chance += COUPON_BASE_BONUS + COUPON_SENSITIVITY_BONUS * self._price_sensitivity
        if calendar.rainfall_mm >= RAIN_THRESHOLD_MM:
            chance *= RAIN_MULTIPLIER
        if calendar.is_weekend:
            chance *= WEEKEND_MULTIPLIER
        if calendar.is_public_holiday:
            chance *= HOLIDAY_MULTIPLIER
        return min(chance, 1.0)

    def step(self, action):
        if self._day is None or self._days_remaining == 0:
            raise RuntimeError("Call reset() before starting a new episode")
        if not self.action_space.contains(action):
            raise ValueError(f"Invalid outreach action: {action!r}")
        requested_action = int(action)
        action = requested_action if self._opted_in else NOTHING
        calendar = self._calendar[self._day]
        visit_probability = self._visit_probability(action, calendar)

        # Keep random draws aligned when comparing actions with a common seed.
        visit_draw, opt_out_draw = self.np_random.random(2)
        visited = bool(visit_draw < visit_probability)
        redeemed_coupon = visited and action == COUPON
        profit = 0
        if visited:
            profit = COUPON_CONTRIBUTION_KRW if redeemed_coupon else FULL_PRICE_CONTRIBUTION_KRW

        self._fatigue = max(0, min(MAX_FATIGUE, self._fatigue + FATIGUE_CHANGES[action]))
        opted_out_today = (
            action != NOTHING
            and self._fatigue >= OPT_OUT_FATIGUE
            and bool(opt_out_draw < OPT_OUT_PROBABILITY)
        )
        if opted_out_today:
            self._opted_in = False
        info = {
            "date": self._day.isoformat(),
            "customer_id": self._customer_id,
            "requested_action": requested_action,
            "action": action,
            "visited": visited,
            "redeemed_coupon": redeemed_coupon,
            "profit_krw": profit,
            "opted_out_today": opted_out_today,
            "fatigue": self._fatigue,
            "opted_in": self._opted_in,
            "visit_probability": visit_probability,
            "rainfall_mm": calendar.rainfall_mm,
            "is_weekend": calendar.is_weekend,
            "is_public_holiday": calendar.is_public_holiday,
        }
        reward = profit if self._reward_fn is None else self._reward_fn(info)
        self._days_remaining -= 1
        terminated = self._days_remaining == 0
        if not terminated:
            self._day += ONE_DAY
        return self._observation(), float(reward), terminated, False, info
