from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationConfig:
    num_users: int = 100
    num_days: int = 100
    seed: int = 42

    # Market and jobs
    base_jobs_per_day: int = 35
    max_job_age_days: int = 21
    initial_open_jobs: int = 120

    # Economy
    starting_wealth_min: float = 250.0
    starting_wealth_max: float = 12000.0
    premium_per_dollar: float = 8.0
    company_revenue_share: float = 0.65
    base_boost_cost: float = 10.0

    # Hiring model
    base_screen_rate: float = 0.05
    base_interview_rate: float = 0.25

    # Quests
    quest_apply_target: int = 3
    quest_message_target: int = 1
    quest_reward_currency: float = 8.0

    # Rare events
    accident_daily_prob: float = 0.0008
    fired_daily_prob: float = 0.0007
    windfall_daily_prob: float = 0.0005
    mass_layoff_daily_prob: float = 0.002

    # Visualization
    dashboard_print_every_n_days: int = 1
