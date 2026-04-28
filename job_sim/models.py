from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


ALL_SKILLS = [
    "python",
    "sql",
    "ml",
    "frontend",
    "backend",
    "cloud",
    "devops",
    "communication",
]


class Strategy(str, Enum):
    REACH = "reach"
    BALANCED = "balanced"
    SAFETY = "safety"


class EmploymentStatus(str, Enum):
    UNEMPLOYED = "unemployed"
    EMPLOYED = "employed"


@dataclass(slots=True)
class Company:
    id: int
    name: str
    tier: int
    boost_revenue: float = 0.0
    applications_received: int = 0
    jobs_filled: int = 0


@dataclass(slots=True)
class ApplicationSubmission:
    applicant_id: int
    boost_multiplier: float
    prep_level: float
    status: str = "pending"


@dataclass(slots=True)
class JobPosting:
    id: int
    company_id: int
    tier: int
    required_skills: dict[str, float]
    salary: float
    days_remaining: int
    applicants: list[ApplicationSubmission] = field(default_factory=list)
    filled_by: int | None = None


@dataclass(slots=True)
class Applicant:
    id: int

    # Fixed traits
    charisma: float
    intelligence: float
    base_experience: float
    spending_willingness: float
    nepotism_company_id: int | None

    # Dynamic traits
    status: EmploymentStatus
    engagement: float
    free_time: float
    wealth: float
    experience: float
    strategy: Strategy
    skills: dict[str, float]

    # Job state
    current_company_id: int | None = None
    current_company_tier: int = 0
    current_salary: float = 0.0
    current_role_skills: list[str] = field(default_factory=list)

    # Resource state
    premium_currency: float = 0.0

    # Adaptive and event state
    recent_rejections: int = 0
    unavailable_days: int = 0
    preparation_bonus: float = 1.0

    # Accumulated stats
    hired_count: int = 0
    total_applications: int = 0
    total_spent_on_boosts: float = 0.0
    total_currency_purchased: float = 0.0
    total_currency_earned_from_quests: float = 0.0
    cumulative_days_unemployed: int = 0

    # Per-day quest counters
    daily_applies: int = 0
    daily_messages: int = 0
    practiced_skills_today: set[str] = field(default_factory=set)
    skill_inactive_days: dict[str, int] = field(default_factory=dict)

    # Optional trace log for user mode
    trace: list[str] = field(default_factory=list)
    trace_by_day: dict[int, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class MarketState:
    job_market_index: float = 1.0
    market_regime: str = "neutral"
