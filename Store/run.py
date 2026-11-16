"""Launch the café simulation and preserve a snapshot of each successful run."""

import argparse
import csv
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from fcntl import LOCK_EX, flock
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_DIR / "results"
HISTORY_FIELDS = ("date", "run_type", "success_metric", "note")
ASSUMPTION_FILES = ("config.py", "env.py", "reward.py")
BASELINE_LOGS = (
    "logs/do_nothing.csv",
    "logs/always_coupon.csv",
    "logs/random_outreach.csv",
    "logs/selective_outreach.csv",
)
V1_EVALUATION_FILES = ("summary_v1.md", "logs/ppo_v1.csv")
V1_TRAINING_FILES = (
    "learning_curve_v1.csv",
    "learning_curve_v1.png",
    "experience_sample_v1.csv",
    "models/v1.zip",
)


@dataclass(frozen=True)
class Task:
    run_type: str
    label: str
    commands: tuple[tuple[str, ...], ...]
    files: tuple[str, ...]
    summary_file: str
    summary_policy: str
    note: str


TASKS = {
    "1": Task(
        "validation",
        "Validate the environment and build the replay",
        (("simulate.py",), ("replay.py",)),
        ("validation.md", *BASELINE_LOGS),
        "validation.md",
        "Do nothing",
        "Baseline validation on the fixed evaluation windows",
    ),
    "2": Task(
        "trial",
        "Run a short PPO trial",
        (("train.py", "--trial"),),
        (),
        "trial.txt",
        "",
        "Trial timings and commands are in trial.txt",
    ),
    "3": Task(
        "training",
        "Train and evaluate the initial PPO policy",
        (("train.py",), ("replay.py",)),
        (*V1_EVALUATION_FILES, *V1_TRAINING_FILES),
        "summary_v1.md",
        "PPO",
        "Initial PPO training followed by held-out evaluation",
    ),
    "4": Task(
        "evaluation",
        "Evaluate the saved PPO v1 policy",
        (("train.py", "--evaluate-only"), ("replay.py",)),
        V1_EVALUATION_FILES,
        "summary_v1.md",
        "PPO",
        "Saved PPO policy on the fixed evaluation windows",
    ),
}


def _run_commands(task, log_path, started):
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"{task.label}\nStarted {started.isoformat(timespec='seconds')}\n")
        for args in task.commands:
            command = (sys.executable, "-u", *args)
            print(f"Running {shlex.join(args)} …", flush=True)
            log.write(f"\n> {shlex.join(command)}\n")
            log.flush()
            subprocess.run(command, cwd=PROJECT_DIR, stdout=log, stderr=subprocess.STDOUT, check=True)


def _snapshot_files(task, snapshot):
    for name in ASSUMPTION_FILES:
        source = PROJECT_DIR / name
        if name != "reward.py" or source.is_file():
            shutil.copy2(source, snapshot / name)
    for name in task.files:
        destination = snapshot / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RESULTS_DIR / name, destination)


def _summary_metric(summary_path, policy):
    """Read reported profit and worst opt-out share from the summary table."""
    header = None
    rows = []
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if header is None:
            if any("profit" in cell.casefold() for cell in cells):
                header = cells
        elif len(cells) == len(header):
            rows.append(cells)

    if not rows:
        return f"See {summary_path.name}"
    row = next((cells for cells in rows if policy.casefold() in cells[0].casefold()), rows[0])
    metrics = [
        f"{label} {value}" for label, value in zip(header, row, strict=True)
        if "profit" in label.casefold() or ("worst" in label.casefold() and "opt" in label.casefold())
    ]
    return " | ".join((row[0], *metrics))


def _archive_path(runs_dir, started, run_type):
    name = f"{started:%Y%m%d_%H%M%S}_{run_type}"
    path = runs_dir / name
    suffix = 2
    while path.exists() or path.with_name(f"{path.name}_failed.log").exists():
        path = runs_dir / f"{name}_{suffix}"
        suffix += 1
    return path


def _stage_history(staged, history, row):
    if history.exists():
        shutil.copyfile(history, staged)
    with staged.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if handle.tell() == 0:
            writer.writerow(HISTORY_FIELDS)
        writer.writerow(row)


def run_task(task):
    runs_dir = RESULTS_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    history = RESULTS_DIR / "run_history.csv"
    with (RESULTS_DIR / ".run.lock").open("a", encoding="utf-8") as lock:
        flock(lock, LOCK_EX)
        started = datetime.now().astimezone()
        archive = _archive_path(runs_dir, started, task.run_type)
        with TemporaryDirectory(dir=runs_dir) as temporary:
            staging = Path(temporary)
            snapshot = staging / "snapshot"
            snapshot.mkdir()
            log_path = snapshot / ("trial.txt" if task.run_type == "trial" else "commands.log")
            try:
                _run_commands(task, log_path, started)
            except subprocess.CalledProcessError as error:
                failed_log = archive.with_name(f"{archive.name}_failed.log")
                with failed_log.open("x", encoding="utf-8") as handle:
                    handle.write(log_path.read_text(encoding="utf-8", errors="replace"))
                print(f"{error.cmd[2]} exited with status {error.returncode}. Details in {failed_log}.", file=sys.stderr)
                return 1

            _snapshot_files(task, snapshot)
            if task.run_type == "trial":
                output = log_path.read_text(encoding="utf-8").splitlines()
                metric = next(
                    (line for line in output if line.startswith("PPO on CPU ran ")),
                    "PPO trial completed",
                )
                for line in output:
                    if line.startswith("Estimated training time "):
                        print(line)
            else:
                metric = _summary_metric(snapshot / task.summary_file, task.summary_policy)
            staged_history = staging / history.name
            _stage_history(
                staged_history,
                history,
                (started.isoformat(timespec="seconds"), task.run_type, metric, task.note),
            )
            snapshot.rename(archive)
            try:
                staged_history.replace(history)
            except OSError:
                archive.rename(snapshot)
                raise
    print(metric)
    print(f"Run saved in {archive}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("choice", nargs="?", choices=("0", *TASKS), help="Run one menu item and exit")
    args = parser.parse_args()
    if args.choice is not None:
        return 0 if args.choice == "0" else run_task(TASKS[args.choice])

    while True:
        print("\nYeouido Riverside Café")
        for number, task in TASKS.items():
            print(f"{number}. {task.label}")
        print("0. Exit")
        try:
            choice = input("Choose a task: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if choice == "0":
            return 0
        if choice in TASKS:
            run_task(TASKS[choice])
        else:
            print("Enter a number from the menu.")


if __name__ == "__main__":
    raise SystemExit(main())
