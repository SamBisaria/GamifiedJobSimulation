from __future__ import annotations

import argparse
import os

from job_sim.config import SimulationConfig
from job_sim.simulation import JobMarketSimulation
from job_sim.visualization import (
    try_write_basic_plots,
    write_company_breakdown_csv,
    write_company_breakdown_json,
    write_daily_metrics_csv,
    write_interaction_events_csv,
    write_summary_json,
    write_applicant_snapshots_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gamified job matching simulation")
    parser.add_argument("--users", type=int, default=100, help="Number of applicants")
    parser.add_argument("--days", type=int, default=100, help="Number of simulation days")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "dashboard", "trace", "all"],
        default="batch",
        help="Output mode",
    )
    parser.add_argument(
        "--trace-id",
        type=int,
        default=0,
        help="Applicant id to trace (for trace/all mode)",
    )
    parser.add_argument(
        "--trace-detail",
        type=str,
        choices=["concise", "full"],
        default="concise",
        help="Trace detail level (default: concise)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "output"),
        help="Directory to write csv/json/plots",
    )
    parser.add_argument(
        "--write-outputs",
        action="store_true",
        help="Write CSV/JSON/plot output files (default: no)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SimulationConfig(num_users=args.users, num_days=args.days, seed=args.seed)
    sim = JobMarketSimulation(config)

    daily = sim.run(mode=args.mode, trace_applicant_id=args.trace_id, trace_detail=args.trace_detail)
    summary = sim.final_summary()
    company_breakdown = sim.company_breakdown()

    csv_path = summary_path = company_csv_path = company_json_path = plot_path = None
    if args.write_outputs:
        csv_path = write_daily_metrics_csv(args.output_dir, daily)
        summary_path = write_summary_json(args.output_dir, summary)
        company_csv_path = write_company_breakdown_csv(args.output_dir, company_breakdown)
        company_json_path = write_company_breakdown_json(args.output_dir, company_breakdown)
        plot_path = try_write_basic_plots(args.output_dir, daily)
        snapshots_path = write_applicant_snapshots_csv(args.output_dir, sim.applicant_snapshots)
        print(f"- Applicant snapshots: {snapshots_path}")
        events_path = write_interaction_events_csv(args.output_dir, sim.interaction_events)
        print(f"- Interaction events: {events_path}")

    print("\nRun complete")
    if args.write_outputs:
        print(f"- CSV metrics: {csv_path}")
        print(f"- Summary: {summary_path}")
        print(f"- Company breakdown CSV: {company_csv_path}")
        print(f"- Company breakdown JSON: {company_json_path}")
        if plot_path:
            print(f"- Plot: {plot_path}")
        else:
            print("- Plot: skipped (matplotlib not installed)")
    else:
        print("- Output files: disabled (use --write-outputs to enable)")

    print("\nFinal summary")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
