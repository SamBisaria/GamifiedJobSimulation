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
    starting_wealth_max: float = 20000.0
    premium_per_dollar: float = 8.0
    company_revenue_share: float = 0.65
    base_boost_cost: float = 10.0

    # Daily living expenses (realistic model)
    # Base costs (food, utilities, etc.) per day
    base_daily_living_cost: float = 35.0  # Base food + utilities minimum
    # Housing cost per day (varies by lifestyle/wealth)
    base_daily_housing_cost: float = 40.0  # Minimum housing; scales with wealth/tier
    # Unemployed efficiency factor (spend less on discretionary items)
    unemployed_expense_factor: float = 0.75

    # Hiring model
    base_screen_rate: float = 0.05
    base_interview_rate: float = 0.25

    # Quests
    quest_apply_target: int = 3
    quest_message_target: int = 1
    quest_reward_currency: float = 8.0

    # Rare events
    accident_daily_prob: float = 0.00005
    fired_daily_prob: float = 0.001
    windfall_daily_prob: float = 0.0005
    mass_layoff_daily_prob: float = 0.02
    chronic_condition_initial_prob: float = 0.04
    chronic_condition_daily_prob: float = 0.0001
    chronic_condition_daily_cost_min: float = 12.0
    chronic_condition_daily_cost_max: float = 65.0
    chronic_condition_free_time_penalty_min: float = 0.06
    chronic_condition_free_time_penalty_max: float = 0.18
    breakdown_daily_prob: float = 0.001
    breakdown_cost_min: float = 300.0
    breakdown_cost_max: float = 3500.0
    accident_severe_prob: float = 0.12
    accident_severe_cost_min: float = 2500.0
    accident_severe_cost_max: float = 12000.0

    # Visualization
    dashboard_print_every_n_days: int = 1

    # Fair mode: disable premium currency and boosts
    fair_mode: bool = False

    # Start all applicants unemployed
    start_unemployed: bool = False
