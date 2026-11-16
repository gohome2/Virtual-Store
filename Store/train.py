"""Train and evaluate the initial PPO policy for Yeouido Riverside Café."""

import argparse
import csv
import json
import os
from datetime import timedelta
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory
from time import perf_counter

import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from config import EPISODE_DAYS, MAX_OPT_OUT_SHARE, RESULTS_DIR
from env import OBSERVATION_FIELDS, CafeEnv
from reward import reward_v1
from simulate import BASELINES, POLICY_LABELS, evaluate_policy

# Reproducible training settings for the CPU trial and initial version.
TRAINING_SEED = 42
TRIAL_STEPS = 2_048
TRAINING_STEPS = 60_416
ROLLOUT_STEPS = 512
BATCH_SIZE = 64
SAMPLE_STEPS = 1_000
MODEL_PATH = RESULTS_DIR / "models" / "v1"
SEASON_NAMES = ("Winter", "Spring", "Summer", "Autumn")


class TrainingRecords(BaseCallback):
    def __init__(self):
        super().__init__()
        self.learning_curve = []
        self.experiences = []
        self.episode_reward = 0.0

    def _on_step(self):
        info = self.locals["infos"][0]
        reward = float(self.locals["rewards"][0])
        self.episode_reward += reward
        if len(self.experiences) < SAMPLE_STEPS:
            state = self.locals["obs_tensor"][0].cpu().tolist()
            next_state = info.get("terminal_observation", self.locals["new_obs"][0]).tolist()
            self.experiences.append((
                self.num_timesteps, info["customer_id"], info["date"],
                json.dumps(dict(zip(OBSERVATION_FIELDS, state, strict=True))),
                info["requested_action"], reward,
                json.dumps(dict(zip(OBSERVATION_FIELDS, next_state, strict=True))),
            ))
        if bool(self.locals["dones"][0]):
            self.learning_curve.append((self.num_timesteps, self.episode_reward))
            self.episode_reward = 0.0
        return True

    def save(self):
        with (RESULTS_DIR / "experience_sample_v1.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["step", "customer_id", "date", "state", "action", "reward", "next_state"])
            writer.writerows(self.experiences)

        averaged = [
            (step, points, mean(points for _, points in self.learning_curve[max(0, index - 49):index + 1]))
            for index, (step, points) in enumerate(self.learning_curve)
        ]
        with (RESULTS_DIR / "learning_curve_v1.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["training_step", "episode_reward", "rolling_mean_reward"])
            writer.writerows(averaged)

        with TemporaryDirectory() as cache:
            os.environ.setdefault("MPLCONFIGDIR", cache)
            import matplotlib

            matplotlib.use("Agg")
            from matplotlib import pyplot as plt

            steps, _, rolling = zip(*averaged, strict=True)
            fig, axis = plt.subplots(figsize=(9, 4.8), layout="constrained")
            axis.plot(steps, rolling, color="#15665a", linewidth=1.7)
            axis.set(
                title="Yeouido Riverside Café · PPO v1",
                xlabel="Training steps",
                ylabel=f"Mean reward per {EPISODE_DAYS}-day customer episode",
            )
            axis.grid(alpha=0.25)
            fig.savefig(RESULTS_DIR / "learning_curve_v1.png", dpi=160)
            plt.close(fig)


def evaluate_v1(model):
    env = CafeEnv(reward_fn=reward_v1)
    try:
        def ppo_policy(observation, _day_index, _rng):
            action, _ = model.predict(observation, deterministic=True)
            return action.item()

        ppo_metrics = evaluate_policy(env, ppo_policy, RESULTS_DIR / "logs" / "ppo_v1.csv")
        baselines = {name: evaluate_policy(env, policy) for name, policy in BASELINES.items()}
    finally:
        env.close()
    rows = {"PPO v1": ppo_metrics, **{POLICY_LABELS[name]: metric for name, metric in baselines.items()}}
    lines = [
        "# Initial PPO evaluation",
        "",
        f"All policies use the same twelve {EPISODE_DAYS}-day windows, customers, and seeds in 2025.",
        f"The opt-out limit is {MAX_OPT_OUT_SHARE:.0%} in every window. Actions shown are the choices the café executed.",
        "",
        "| Policy | Mean 30-day profit (KRW) | Mean opt-outs | Worst opt-outs | Meets limit | Mean daily visitors | Nothing | Messages | Coupons |",
        "| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: |",
    ]
    for name, metric in rows.items():
        within_limit = "Yes" if metric.worst_opt_out_share <= MAX_OPT_OUT_SHARE else "No"
        actions = metric.executed_actions
        lines.append(
            f"| {name} | {metric.average_profit_krw:,.0f} | {metric.average_opt_out_share:.1%} | "
            f"{metric.worst_opt_out_share:.1%} | {within_limit} | {metric.average_daily_visitors:.1f} | "
            f"{actions['nothing']:,} | {actions['message']:,} | {actions['coupon']:,} |"
        )

    reference = baselines["selective_outreach"]
    delta = ppo_metrics.average_profit_krw - reference.average_profit_krw
    lines.extend((
        "",
        f"Difference from selective weekly outreach in mean 30-day profit: {delta:+,.0f} KRW.",
        "Reward v1 uses contribution profit alone. Actual opt-outs are evaluated against the separate limit.",
    ))
    reference_label = POLICY_LABELS["selective_outreach"]
    seasonal_windows = {
        label: {season: [] for season in SEASON_NAMES}
        for label in ("PPO v1", reference_label)
    }
    for label, groups in seasonal_windows.items():
        for window in rows[label].windows:
            midpoint = window.start_date + timedelta(days=EPISODE_DAYS // 2)
            season = SEASON_NAMES[(midpoint.month % 12) // 3]
            groups[season].append(window)
    lines.extend((
        "",
        "## Results by season",
        "",
        "Seasons follow Seoul's calendar. Spring is March–May, summer June–August, "
        "autumn September–November, and winter December–February.",
        "Each 30-day window is grouped by its midpoint date. Each season contains "
        "three evaluation windows. Some windows span the transition between seasons.",
        "",
        "| Season | PPO mean profit (KRW) | Weekly rule mean profit (KRW) | PPO worst opt-outs | Weekly rule worst opt-outs |",
        "| --- | ---: | ---: | ---: | ---: |",
    ))
    for season in SEASON_NAMES:
        ppo_windows = seasonal_windows["PPO v1"][season]
        weekly_windows = seasonal_windows[reference_label][season]
        lines.append(
            f"| {season} | {mean(window.profit_krw for window in ppo_windows):,.0f} | "
            f"{mean(window.profit_krw for window in weekly_windows):,.0f} | "
            f"{max(window.opt_out_share for window in ppo_windows):.1%} | "
            f"{max(window.opt_out_share for window in weekly_windows):.1%} |"
        )
    (RESULTS_DIR / "summary_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PPO v1 mean {EPISODE_DAYS}-day profit: ₩{ppo_metrics.average_profit_krw:,.0f}.")
    print(f"Worst evaluation window opt-out share: {ppo_metrics.worst_opt_out_share:.1%}.")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    mode = cli.add_mutually_exclusive_group()
    mode.add_argument("--trial", action="store_true", help="check a short run and report its speed")
    mode.add_argument("--evaluate-only", action="store_true", help="evaluate the saved v1 model")
    args = cli.parse_args()
    torch.set_num_threads(1)

    if args.evaluate_only:
        model_file = Path(f"{MODEL_PATH}.zip")
        if not model_file.is_file():
            raise SystemExit("Run initial training to create results/models/v1.zip.")
        evaluate_v1(PPO.load(model_file, device="cpu"))
        return

    env = CafeEnv(reward_fn=reward_v1)
    try:
        model = PPO("MlpPolicy", env, n_steps=ROLLOUT_STEPS, batch_size=BATCH_SIZE, seed=TRAINING_SEED, device="cpu")
        records = TrainingRecords()
        started = perf_counter()
        model.learn(total_timesteps=TRIAL_STEPS if args.trial else TRAINING_STEPS, callback=records)
        elapsed = perf_counter() - started
        milliseconds = elapsed / model.num_timesteps * 1000
        print(f"PPO on CPU ran {model.num_timesteps:,} steps in {elapsed:.2f} s ({milliseconds:.2f} ms per step).")
        if args.trial:
            forecast = elapsed / model.num_timesteps * TRAINING_STEPS
            print(f"Estimated training time for {TRAINING_STEPS:,} main steps: {forecast:.0f} s, plus evaluation.")
            return
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        model.save(MODEL_PATH)
        records.save()
        evaluate_v1(model)
    finally:
        env.close()


if __name__ == "__main__":
    main()
