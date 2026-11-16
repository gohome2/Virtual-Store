"""Run the four café baselines on the fixed held-out evaluation windows."""

import csv
import json
import random
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory

from config import EPISODE_DAYS, EVALUATION_RUNS, EVALUATION_START, MAX_OPT_OUT_SHARE, RESULTS_DIR
from env import (
    ACTION_NAMES,
    BASE_VISIT_PROBABILITY,
    COUPON,
    COUPON_BASE_BONUS,
    COUPON_CONTRIBUTION_KRW,
    COUPON_SENSITIVITY_BONUS,
    FULL_PRICE_CONTRIBUTION_KRW,
    HOLIDAY_MULTIPLIER,
    MESSAGE,
    MESSAGE_VISIT_BONUS,
    NOTHING,
    RAIN_THRESHOLD_MM,
    WEEKEND_MULTIPLIER,
    CafeEnv,
)

OBSERVATION_FIELDS = (
    "price_sensitivity",
    "fatigue_fraction",
    "opted_in",
    "is_weekend",
    "is_public_holiday",
    "days_remaining_fraction",
)
LOG_FIELDS = ("date", "target", "state", "action", "reaction", "profit")
WEEK_LENGTH_DAYS = 7
WEATHER_CONDITIONS = {
    (False, False, False): "dry_weekday",
    (True, False, False): "rainy_weekday",
    (False, True, False): "dry_weekend",
    (False, False, True): "dry_holiday",
}

Policy = Callable[[Sequence[float], int, random.Random], int]


@dataclass(frozen=True)
class WindowMetrics:
    start_date: date
    seed: int
    profit_krw: float
    opt_out_share: float
    average_daily_visitors: float
    peak_daily_visitors: int


@dataclass(frozen=True)
class PolicyMetrics:
    windows: tuple[WindowMetrics, ...]
    average_profit_krw: float
    average_opt_out_share: float
    worst_opt_out_share: float
    average_daily_visitors: float
    peak_daily_visitors: int
    executed_actions: dict[str, int]
    coupon_redemptions: int
    condition_visit_probabilities: dict[str, float]


@contextmanager
def _open_log(path: Path | str | None):
    if path is None:
        yield None
        return

    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=log_path.parent) as temp_dir:
        temp_path = Path(temp_dir) / log_path.name
        with temp_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(LOG_FIELDS)
            yield writer
        temp_path.replace(log_path)


def _write_step(writer, observation, reward, info):
    state = dict(zip(OBSERVATION_FIELDS, map(float, observation), strict=True))
    reaction = {
        "requested_action": int(info["requested_action"]),
        "visited": bool(info["visited"]),
        "redeemed_coupon": bool(info["redeemed_coupon"]),
        "opted_out_today": bool(info["opted_out_today"]),
        "fatigue": float(info["fatigue"]),
        "opted_in": bool(info["opted_in"]),
        "visit_probability": float(info["visit_probability"]),
        "rainfall_mm": float(info["rainfall_mm"]),
        "is_weekend": bool(info["is_weekend"]),
        "is_public_holiday": bool(info["is_public_holiday"]),
        "reward": float(reward),
    }
    writer.writerow(
        (
            info["date"],
            int(info["customer_id"]),
            json.dumps(state, separators=(",", ":")),
            int(info["action"]),
            json.dumps(reaction, separators=(",", ":")),
            info["profit_krw"],
        )
    )


def _weather_condition(info):
    rainy = info["rainfall_mm"] >= RAIN_THRESHOLD_MM
    return WEATHER_CONDITIONS.get((rainy, info["is_weekend"], info["is_public_holiday"]))


def evaluate_policy(
    env: CafeEnv, policy: Policy, log_path: Path | str | None = None
) -> PolicyMetrics:
    """Evaluate every customer in each window using fixed environment and policy seeds."""
    customer_ids = env.customer_ids
    if not customer_ids:
        raise ValueError("Evaluation requires at least one customer")

    windows = []
    actions = Counter(dict.fromkeys(ACTION_NAMES, 0))
    probability_sums = Counter()
    probability_counts = Counter()
    coupon_redemptions = 0

    with _open_log(log_path) as writer:
        for start_date, seed in EVALUATION_RUNS:
            profit_krw = 0.0
            opt_outs = 0
            daily_visitors = Counter()
            for customer_id in customer_ids:
                environment_rng = random.Random(f"environment:{seed}:{customer_id}")
                policy_rng = random.Random(f"policy:{seed}:{customer_id}")
                observation, _ = env.reset(
                    seed=environment_rng.getrandbits(64),
                    options={"customer_id": customer_id, "start_date": start_date},
                )
                for day_index in range(EPISODE_DAYS):
                    action = int(policy(observation, day_index, policy_rng))
                    next_observation, reward, terminated, truncated, info = env.step(action)
                    if (terminated or truncated) != (day_index == EPISODE_DAYS - 1):
                        raise RuntimeError(
                            f"Unexpected episode length for customer {customer_id} "
                            f"in the window starting {start_date}"
                        )

                    daily_visitors[info["date"]] += int(info["visited"])
                    profit_krw += info["profit_krw"]
                    opt_outs += int(info["opted_out_today"])
                    actions[ACTION_NAMES[info["action"]]] += 1
                    coupon_redemptions += int(info["redeemed_coupon"])
                    condition = _weather_condition(info)
                    if condition is not None:
                        probability_sums[condition] += info["visit_probability"]
                        probability_counts[condition] += 1
                    if writer is not None:
                        _write_step(writer, observation, reward, info)
                    observation = next_observation

            windows.append(
                WindowMetrics(
                    start_date=start_date,
                    seed=seed,
                    profit_krw=profit_krw,
                    opt_out_share=opt_outs / len(customer_ids),
                    average_daily_visitors=sum(daily_visitors.values()) / EPISODE_DAYS,
                    peak_daily_visitors=max(daily_visitors.values()),
                )
            )

    return PolicyMetrics(
        windows=tuple(windows),
        average_profit_krw=mean(window.profit_krw for window in windows),
        average_opt_out_share=mean(window.opt_out_share for window in windows),
        worst_opt_out_share=max(window.opt_out_share for window in windows),
        average_daily_visitors=mean(window.average_daily_visitors for window in windows),
        peak_daily_visitors=max(window.peak_daily_visitors for window in windows),
        executed_actions=dict(actions),
        coupon_redemptions=coupon_redemptions,
        condition_visit_probabilities={
            condition: probability_sums[condition] / count
            for condition, count in probability_counts.items()
        },
    )


def do_nothing(_observation, _day_index, _rng):
    return NOTHING


def always_coupon(_observation, _day_index, _rng):
    return COUPON


def random_outreach(_observation, _day_index, rng):
    return rng.randrange(len(ACTION_NAMES))


def selective_outreach(observation, day_index, _rng):
    price_sensitivity, _, opted_in, *_ = observation
    if not opted_in or day_index % WEEK_LENGTH_DAYS:
        return NOTHING

    message_value = (
        BASE_VISIT_PROBABILITY + MESSAGE_VISIT_BONUS
    ) * FULL_PRICE_CONTRIBUTION_KRW
    coupon_probability = (
        BASE_VISIT_PROBABILITY
        + COUPON_BASE_BONUS
        + COUPON_SENSITIVITY_BONUS * price_sensitivity
    )
    if coupon_probability * COUPON_CONTRIBUTION_KRW > message_value:
        return COUPON
    return MESSAGE


BASELINES: dict[str, Policy] = {
    "do_nothing": do_nothing,
    "always_coupon": always_coupon,
    "random_outreach": random_outreach,
    "selective_outreach": selective_outreach,
}

POLICY_LABELS = {
    "do_nothing": "Do nothing",
    "always_coupon": "Request a coupon every day",
    "random_outreach": "Random outreach",
    "selective_outreach": "Selective weekly outreach",
}


def validation_markdown(results: dict[str, PolicyMetrics]) -> str:
    baseline = results["do_nothing"]
    periods = len(baseline.windows)
    customer_count = sum(baseline.executed_actions.values()) // (periods * EPISODE_DAYS)
    lines = [
        "# Environment validation",
        "",
        f"Each rule used all {customer_count} customers in {periods} fixed "
        f"{EPISODE_DAYS}-day windows in {EVALUATION_START.year}.",
        "Profit is the mean total café contribution per window. Opt-out shares are the "
        "mean and highest shares among the windows. Coupon redemptions are the total across all windows.",
        "",
        f"| Rule | Mean {EPISODE_DAYS}-day profit (KRW) | Mean opt-outs | Worst opt-outs | "
        "Meets opt-out limit in every window | Mean daily visitors | Busiest day | Coupon redemptions |",
        "| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: |",
    ]
    for name, result in results.items():
        meets_limit = "Yes" if result.worst_opt_out_share <= MAX_OPT_OUT_SHARE else "No"
        lines.append(
            f"| {POLICY_LABELS[name]} | {result.average_profit_krw:,.0f} | "
            f"{result.average_opt_out_share:.1%} | {result.worst_opt_out_share:.1%} | "
            f"{meets_limit} | {result.average_daily_visitors:.1f} | "
            f"{result.peak_daily_visitors} | {result.coupon_redemptions:,} |"
        )

    highest_profit = max(results, key=lambda name: results[name].average_profit_krw)
    within_limit = [
        name for name, result in results.items()
        if result.worst_opt_out_share <= MAX_OPT_OUT_SHARE
    ]
    best_within_limit = max(
        within_limit,
        key=lambda name: results[name].average_profit_krw,
        default=None,
    )
    best_label = POLICY_LABELS[best_within_limit] if best_within_limit else "None"
    baseline_weather = baseline.condition_visit_probabilities
    lines += [
        "",
        "The weekly rule contacts opted-in customers once every seven days and rests "
        "on the other days. It chooses a coupon when its predicted contribution exceeds "
        "the contribution from a full-price visit prompted by a message.",
        "The daily coupon rule requests a coupon for every customer. The environment "
        "executes no outreach for customers who opt out.",
        "",
        "## Checks",
        "",
        f"- Highest mean profit: {POLICY_LABELS[highest_profit]}. Highest mean profit "
        f"within the {MAX_OPT_OUT_SHARE:.0%} opt-out limit in every window: {best_label}.",
    ]
    if best_within_limit in (None, "always_coupon"):
        lines.append("- Review whether daily maximum outreach should qualify as the best rule.")
    if len({result.average_profit_krw for result in results.values()}) < len(results):
        lines.append("- Review tied profit results for policies expected to behave differently.")

    maximum_expected_visits = customer_count * min(
        1.0,
        (BASE_VISIT_PROBABILITY + COUPON_BASE_BONUS + COUPON_SENSITIVITY_BONUS)
        * WEEKEND_MULTIPLIER
        * HOLIDAY_MULTIPLIER,
    )
    busiest_rule = max(results, key=lambda name: results[name].average_daily_visitors)
    mean_visitors = results[busiest_rule].average_daily_visitors
    status = "Pass" if mean_visitors <= maximum_expected_visits else "Review"
    lines.append(
        f"- {status}: the busiest rule averaged {mean_visitors:.1f} visitors per day. "
        f"The assumed upper bound on expected daily visits is {maximum_expected_visits:.1f}. "
        "Individual days can exceed that expectation by chance."
    )

    for condition, label, direction in (
        ("rainy_weekday", "rainy weekdays", -1),
        ("dry_weekend", "dry weekends", 1),
        ("dry_holiday", "dry weekday holidays", 1),
    ):
        if "dry_weekday" not in baseline_weather or condition not in baseline_weather:
            lines.append(f"- No matched observations for {label} in the evaluation windows.")
            continue
        ordinary = baseline_weather["dry_weekday"]
        matched = baseline_weather[condition]
        status = "Pass" if direction * (matched - ordinary) > 0 else "Review"
        lines.append(
            f"- {status}: under no outreach, the mean modeled visit chance on {label} "
            f"was {matched:.1%}, compared with {ordinary:.1%} on dry weekdays."
        )

    return "\n".join(lines) + "\n"


def run_validation(results_dir: Path = RESULTS_DIR) -> dict[str, PolicyMetrics]:
    """Save the latest baseline logs and validation report."""
    results_dir = Path(results_dir)
    env = CafeEnv()
    try:
        results = {
            name: evaluate_policy(env, policy, results_dir / "logs" / f"{name}.csv")
            for name, policy in BASELINES.items()
        }
    finally:
        env.close()
    (results_dir / "validation.md").write_text(validation_markdown(results), encoding="utf-8")
    return results


if __name__ == "__main__":
    run_validation()
    print(f"Wrote baseline logs and validation report to {RESULTS_DIR}")
