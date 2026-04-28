from __future__ import annotations

import csv
import json
import os
from datetime import datetime


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_daily_metrics_csv(output_dir: str, daily_metrics: list[dict[str, float | int | str]]) -> str:
    ensure_dir(output_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(output_dir, f"daily_metrics_{stamp}.csv")
    if not daily_metrics:
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write("day\n")
        return target

    fieldnames = list(daily_metrics[0].keys())
    with open(target, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(daily_metrics)
    return target


def write_summary_json(output_dir: str, summary: dict[str, float | int]) -> str:
    ensure_dir(output_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(output_dir, f"summary_{stamp}.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return target


def write_company_breakdown_csv(output_dir: str, rows: list[dict[str, float | int | str]]) -> str:
    ensure_dir(output_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(output_dir, f"company_breakdown_{stamp}.csv")
    if not rows:
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write("company_id\n")
        return target

    fieldnames = list(rows[0].keys())
    with open(target, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return target


def write_company_breakdown_json(output_dir: str, rows: list[dict[str, float | int | str]]) -> str:
    ensure_dir(output_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(output_dir, f"company_breakdown_{stamp}.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    return target


def try_write_basic_plots(output_dir: str, daily_metrics: list[dict[str, float | int | str]]) -> str | None:
    if not daily_metrics:
        return None

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    ensure_dir(output_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(output_dir, f"metrics_plot_{stamp}.png")

    days = [row["day"] for row in daily_metrics]
    employment = [row["employment_rate"] for row in daily_metrics]
    boost_spend = [row["boost_spend_today"] for row in daily_metrics]
    market = [row["market_index"] for row in daily_metrics]

    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(9, 9), sharex=True)
    axes[0].plot(days, employment)
    axes[0].set_ylabel("Employment rate")
    axes[0].set_title("Simulation Daily Metrics")

    axes[1].plot(days, boost_spend)
    axes[1].set_ylabel("Boost spend ($)")

    axes[2].plot(days, market)
    axes[2].set_ylabel("Market index")
    axes[2].set_xlabel("Day")

    plt.tight_layout()
    plt.savefig(target)
    plt.close(fig)
    return target
