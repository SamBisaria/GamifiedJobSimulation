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
    parser.add_argument(
        "--fair-mode",
        action="store_true",
        help="Disable premium currency purchases and boosts (fair competition mode)",
    )
    parser.add_argument(
        "--start-unemployed",
        action="store_true",
        help="Start all applicants unemployed",
    )
    parser.add_argument(
        "--fair-dir", 
        default=None, 
        help="Output dir from a --fair-mode run for comparison"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SimulationConfig(
        num_users=args.users,
        num_days=args.days,
        seed=args.seed,
        fair_mode=args.fair_mode,
        start_unemployed=args.start_unemployed,
    )
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

    print("\n" + "=" * 80)
    print("RUN COMPLETE")
    print("=" * 80)
    
    if args.write_outputs:
        print("\nOutput files:")
        print(f"  CSV metrics:          {csv_path}")
        print(f"  Summary:              {summary_path}")
        print(f"  Company breakdown:    {company_csv_path}")
        print(f"  Company breakdown:    {company_json_path}")
        if plot_path:
            print(f"  Plot:                 {plot_path}")
        else:
            print("  Plot:                 skipped (matplotlib not installed)")
    else:
        print("Output files: disabled (use --write-outputs to enable)")

    print("\n" + "-" * 80)
    print("FINAL SUMMARY")
    print("-" * 80)
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key:.<40} {value:>10.4f}" if "rate" in key or "tier" in key or "score" in key else f"{key:.<40} ${value:>10.2f}" if "revenue" in key or "spend" in key or "currency" in key else f"{key:.<40} {value:>10.2f}")
        else:
            print(f"{key:.<40} {value:>10}")
    
    # Print enhanced summary if available
    try:
        detailed = sim.final_summary_detailed()
        print("\n" + "-" * 80)
        print("RARE EVENTS DURING SIMULATION")
        print("-" * 80)
        events = detailed["rare_events"]
        if (
            events["accidents"] > 0
            or events["firings"] > 0
            or events["windfalls"] > 0
            or events["mass_layoffs"] > 0
            or events["chronic_conditions"] > 0
            or events["breakdowns"] > 0
        ):
            print(f"Accidents:                         {events['accidents']}")
            if events["severe_accidents"] > 0:
                print(f"  → Severe accidents:              {events['severe_accidents']}")
            print(f"Chronic conditions:                {events['chronic_conditions']}")
            print(f"Breakdowns (car/house):            {events['breakdowns']}")
            print(f"Firings:                           {events['firings']}")
            print(f"Windfalls (lucky finds):           {events['windfalls']}")
            print(f"Mass layoffs:                      {events['mass_layoffs']}")
            if events["mass_layoffs"] > 0:
                print(f"  → {events['people_affected_by_layoffs']} people affected")
        else:
            print("(No major events occurred during this simulation)")
        
        print("\n" + "-" * 80)
        print("INDIVIDUAL ACHIEVEMENTS")
        print("-" * 80)
        achievements = detailed["individual_achievements"]
        if achievements["top_earner"]:
            print(f"Top earner (Applicant {achievements['top_earner']['applicant_id']}):        ${achievements['top_earner']['salary']:>10.2f}/year")
        print(f"Richest person (Applicant {achievements['richest_person']['applicant_id']}):   ${achievements['richest_person']['final_wealth']:>10.2f}")
        if achievements["biggest_tier_jump"]["tier_improvement"] > 0:
            print(f"Biggest tier jump (Applicant {achievements['biggest_tier_jump']['applicant_id']}):  +{achievements['biggest_tier_jump']['tier_improvement']} tiers")
        else:
            print(f"Biggest tier change (Applicant {achievements['biggest_tier_jump']['applicant_id']}): {achievements['biggest_tier_jump']['tier_improvement']:+d} tiers")
        
        print("\n" + "-" * 80)
        print("ECONOMICS SUMMARY")
        print("-" * 80)
        econ = detailed["economics"]
        print(f"Total applications:               {econ['total_applications']:>8}")
        print(f"Total jobs filled:                {econ['total_jobs_filled']:>8}")
        print(f"Boost spend (applicants):         ${econ['total_boost_spend']:>10.2f}")
        print(f"Company boost revenue:            ${econ['total_company_revenue']:>10.2f}")
        print(f"Platform net revenue:             ${econ['total_platform_revenue']:>10.2f}")
    except Exception:
        pass  # If detailed summary fails, just show the basic one
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
