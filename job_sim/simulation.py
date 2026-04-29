from __future__ import annotations

import math
import random

from .config import SimulationConfig
from .models import (
    ALL_SKILLS,
    Applicant,
    ApplicationSubmission,
    Company,
    EmploymentStatus,
    JobPosting,
    MarketState,
    Strategy,
)
from .trace import (
    build_daily_status_window,
    build_trace_start_end_summary,
    build_trace_start_snapshot,
)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


COMPANY_NAME_POOLS: dict[int, list[str]] = {
    5: [
        "Boogle",
        "Rainforest",
        "Banana",
        "Macrohard",
        "ZuckCo",
        "ClosedGPT",
        "SalesForge",
        "PalanTrack",
    ],
    4: [
        "Stripeway",
        "Snowpeak",
        "ScaleGrid",
        "BlockDock",
        "ByteSpring",
        "NeonStack",
        "QuantumLane",
        "CipherNest",
        "OrbitWorks",
        "SummitOps",
        "BlueHarbor",
        "Northstar Labs",
    ],
    3: [
        "Cedar Systems",
        "Riverline Tech",
        "Granite Apps",
        "BrightCircuit",
        "SilverPixel",
        "Anchor Software",
        "Pinecone Data",
        "Mainline Cloud",
        "Horizon Analytics",
        "Keystone Digital",
        "Autumn Byte",
        "Beacon Logic",
    ],
    2: [
        "Maple Solutions",
        "Harbor IT",
        "Metro Logic",
        "Peakline Apps",
        "BlueSky Systems",
        "Compass Code",
        "CloudRail",
        "Lakeside Software",
        "Twin Oaks Tech",
        "Cobalt Services",
        "EdgePoint Labs",
        "Prairie Networks",
    ],
    1: [
        "LocalByte",
        "Cornerstone IT",
        "Smalltown Software",
        "QuickFix Labs",
        "Oak Street Tech",
        "BudgetStack",
        "Neighborhood Systems",
        "SimplePath Digital",
        "Starterline Apps",
        "Everyday Code Co",
        "Launchpad Dev",
        "FreshDesk Tech",
    ],
}


class JobMarketSimulation:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.market = MarketState()
        self.fair_mode = config.fair_mode

        self.applicant_snapshots: list[dict[str, int | float | str]] = []
        self.interaction_events: list[dict[str, int | str]] = []

        self.next_job_id = 1
        self._trace_enabled = False
        self._trace_applicant_id = 0
        self._trace_detail = "concise"
        self._trace_previous_snapshot: dict[str, object] | None = None
        self._trace_start_snapshot: dict[str, object] | None = None
        self._trace_status_windows_by_day: dict[int, str] = {}

        # Event tracking for summary statistics
        self._total_accidents = 0
        self._total_severe_accidents = 0
        self._total_firings = 0
        self._total_windfalls = 0
        self._total_mass_layoffs = 0
        self._total_affected_by_mass_layoff = 0
        self._total_chronic_conditions = 0
        self._total_breakdowns = 0

        self.companies: list[Company] = self._build_companies()
        self.applicants: list[Applicant] = self._build_applicants()
        self.jobs: list[JobPosting] = []
        self.daily_metrics: list[dict[str, float | int | str]] = []

        self._applications_today = 0
        self._hires_today = 0
        self._boost_spend_today = 0.0
        self._currency_purchased_today = 0.0
        self._quest_currency_today = 0.0
        self._seed_initial_jobs()

    def run(
        self,
        mode: str = "batch",
        trace_applicant_id: int = 0,
        trace_detail: str = "concise",
    ) -> list[dict[str, float | int | str]]:
        self._trace_enabled = mode in {"trace", "all"}
        self._trace_applicant_id = trace_applicant_id
        self._trace_detail = trace_detail
        self._trace_previous_snapshot = None
        self._trace_start_snapshot = None
        self._trace_status_windows_by_day = {}

        if self._trace_enabled and 0 <= self._trace_applicant_id < len(self.applicants):
            self._trace_start_snapshot = self._capture_snapshot(self.applicants[self._trace_applicant_id])
            print(build_trace_start_snapshot(self._trace_applicant_id, self._trace_start_snapshot, ALL_SKILLS))

        for day in range(1, self.config.num_days + 1):
            metrics = self.step_day(day)
            self.daily_metrics.append(metrics)

            if mode in {"dashboard", "all"} and day % self.config.dashboard_print_every_n_days == 0:
                print(
                    f"Day {day:03d} | emp={metrics['employment_rate']:.2%} "
                    f"open_jobs={metrics['open_jobs']} hires={metrics['hires_today']} "
                    f"boost_spend=${metrics['boost_spend_today']:.2f} market={metrics['market_index']:.2f}"
                )

            if mode in {"trace", "all"}:
                daily_trace = self.get_applicant_day_trace(trace_applicant_id, day)
                print(f"Trace user {trace_applicant_id} | Day {day:03d} events:")
                if daily_trace:
                    for entry in daily_trace:
                        print(f"  - {entry}")
                else:
                    print("  - no notable actions")

                status_window = self._trace_status_windows_by_day.get(day)
                if status_window:
                    print(status_window)

        if mode in {"trace", "all"} and 0 <= self._trace_applicant_id < len(self.applicants):
            end_snapshot = self._capture_snapshot(self.applicants[self._trace_applicant_id])
            print(
                build_trace_start_end_summary(
                    self._trace_applicant_id,
                    self._trace_start_snapshot,
                    end_snapshot,
                    ALL_SKILLS,
                )
            )

        return self.daily_metrics

    def step_day(self, day: int) -> dict[str, float | int | str]:
        self._reset_daily_counters()
        self._apply_daily_income_and_expenses()
        self._update_market_state()
        self._expire_and_refresh_jobs()

        for applicant in self.applicants:
            self._run_applicant_day(day, applicant)

        self._process_hiring(day)
        self._apply_random_events(day)
        self._adapt_strategies()
        self._apply_chronic_effects()
        self._apply_skill_maintenance()

        if self._trace_enabled and 0 <= self._trace_applicant_id < len(self.applicants):
            self._log_daily_snapshot(self.applicants[self._trace_applicant_id], day)

        self._collect_applicant_snapshots(day)

        return self._collect_metrics(day)

    def _company_name(self, company_id: int) -> str:
        return self.companies[company_id - 1].name

    def _build_companies(self) -> list[Company]:
        companies: list[Company] = []
        available_names = {tier: names[:] for tier, names in COMPANY_NAME_POOLS.items()}
        for idx in range(1, 31):
            tier_roll = self.rng.random()
            if tier_roll < 0.10:
                tier = 5
            elif tier_roll < 0.25:
                tier = 4
            elif tier_roll < 0.55:
                tier = 3
            elif tier_roll < 0.80:
                tier = 2
            else:
                tier = 1

            if available_names[tier]:
                name = self.rng.choice(available_names[tier])
                available_names[tier].remove(name)
            else:
                # Fallback only if a tier pool is exhausted.
                name = f"Tier{tier}Co_{idx}"

            companies.append(Company(id=idx, name=name, tier=tier))
        return companies

    def _build_applicants(self) -> list[Applicant]:
        applicants: list[Applicant] = []
        for idx in range(self.config.num_users):
            intelligence = clamp(self.rng.gauss(0.55, 0.18), 0.1, 0.99)
            charisma = clamp(self.rng.gauss(0.50, 0.20), 0.1, 0.99)
            base_experience = clamp(self.rng.gauss(0.35, 0.25), 0.0, 1.0)
            spending_willingness = clamp(self.rng.betavariate(2, 3), 0.02, 0.98)
            engagement = clamp(self.rng.gauss(0.6, 0.2), 0.1, 1.0)
            free_time = clamp(self.rng.gauss(0.6, 0.2), 0.1, 1.0)
            wealth = self.rng.uniform(self.config.starting_wealth_min, self.config.starting_wealth_max)

            if self.config.start_unemployed:
                status = EmploymentStatus.UNEMPLOYED
            else:
                status = EmploymentStatus.EMPLOYED if self.rng.random() < 0.62 else EmploymentStatus.UNEMPLOYED
            strategy_roll = self.rng.random()
            if strategy_roll < 0.25:
                strategy = Strategy.REACH
            elif strategy_roll < 0.70:
                strategy = Strategy.BALANCED
            else:
                strategy = Strategy.SAFETY

            skills = {
                skill: clamp(self.rng.gauss(0.25 + 0.55 * intelligence, 0.2), 0.0, 1.0)
                for skill in ALL_SKILLS
            }

            nepotism_company_id = None
            if self.rng.random() < 0.10 and wealth > 6500:
                nepotism_company_id = self.rng.choice(self.companies).id

            applicant = Applicant(
                id=idx,
                charisma=charisma,
                intelligence=intelligence,
                base_experience=base_experience,
                spending_willingness=spending_willingness,
                nepotism_company_id=nepotism_company_id,
                status=status,
                engagement=engagement,
                free_time=free_time,
                wealth=wealth,
                experience=base_experience,
                strategy=strategy,
                skills=skills,
            )

            if self.rng.random() < self.config.chronic_condition_initial_prob:
                self._activate_chronic_condition(applicant, 0, "initial")

            initial_cap = self._skill_cap(applicant)
            for skill_name in ALL_SKILLS:
                applicant.skills[skill_name] = clamp(applicant.skills[skill_name], 0.0, initial_cap)

            if status == EmploymentStatus.EMPLOYED:
                employer = self.rng.choice(self.companies)
                applicant.current_company_id = employer.id
                applicant.current_company_tier = employer.tier
                applicant.current_salary = self._salary_for_tier(employer.tier)
                applicant.current_role_skills = self.rng.sample(ALL_SKILLS, k=3)

            applicant.skill_inactive_days = {skill: 0 for skill in ALL_SKILLS}
            applicants.append(applicant)
        return applicants

    def _seed_initial_jobs(self) -> None:
        for _ in range(self.config.initial_open_jobs):
            self.jobs.append(self._create_random_job())

    def _create_random_job(self) -> JobPosting:
        company = self.rng.choice(self.companies)
        required_skills = {skill: self.rng.uniform(0.2, 1.0) for skill in self.rng.sample(ALL_SKILLS, k=4)}
        salary = self._salary_for_tier(company.tier)
        job = JobPosting(
            id=self.next_job_id,
            company_id=company.id,
            tier=company.tier,
            required_skills=required_skills,
            salary=salary,
            days_remaining=self.rng.randint(7, self.config.max_job_age_days),
        )
        self.next_job_id += 1
        return job

    def _salary_for_tier(self, tier: int) -> float:
        base = {1: 42000, 2: 62000, 3: 90000, 4: 130000, 5: 190000}[tier]
        noise = self.rng.uniform(-0.18, 0.22)
        return round(base * (1.0 + noise), 2)

    def _activate_chronic_condition(self, applicant: Applicant, day: int, reason: str) -> None:
        if applicant.chronic_condition:
            return
        applicant.chronic_condition = True
        applicant.chronic_daily_cost = self.rng.uniform(
            self.config.chronic_condition_daily_cost_min,
            self.config.chronic_condition_daily_cost_max,
        )
        applicant.chronic_free_time_penalty = self.rng.uniform(
            self.config.chronic_condition_free_time_penalty_min,
            self.config.chronic_condition_free_time_penalty_max,
        )
        self._total_chronic_conditions += 1
        self._log_trace(applicant, day, f"chronic condition onset ({reason})")

    def _apply_daily_income_and_expenses(self) -> None:
        """Apply realistic daily income and expenses based on employment status and wealth."""
        for applicant in self.applicants:
            # Daily salary income for employed people
            if applicant.status == EmploymentStatus.EMPLOYED:
                daily_salary = applicant.current_salary / 365.0
                applicant.wealth += daily_salary
            
            # Calculate and subtract daily living expenses
            daily_expense = self._calculate_daily_expense(applicant)
            applicant.wealth = max(0.0, applicant.wealth - daily_expense)

    def _calculate_daily_expense(self, applicant: Applicant) -> float:
        """Calculate realistic daily living expenses (without randomness for planning purposes)."""
        if applicant.status == EmploymentStatus.EMPLOYED:
            # Employed: baseline living costs + lifestyle spending based on income tier
            base_expense = self.config.base_daily_living_cost + self.config.base_daily_housing_cost
            
            # Lifestyle adjustment: richer people live more expensively but still save
            # Tier 5 person spends more on housing and lifestyle than tier 1
            tier_factor = 0.8 + 0.3 * (applicant.current_company_tier / 5.0)
            lifestyle_expense = base_expense * tier_factor
            
            # Add randomness to daily costs (±25%)
            cost_noise = self.rng.uniform(0.75, 1.25)
            return lifestyle_expense * cost_noise
        else:
            # Unemployed: baseline living costs, more frugal on lifestyle
            base_expense = self.config.base_daily_living_cost + self.config.base_daily_housing_cost
            
            # Unemployed people are frugal: reduce discretionary spending
            frugal_expense = base_expense * self.config.unemployed_expense_factor
            
            # Add randomness (±20%)
            cost_noise = self.rng.uniform(0.80, 1.20)
            return frugal_expense * cost_noise

    def _apply_chronic_effects(self) -> None:
        for applicant in self.applicants:
            if not applicant.chronic_condition:
                continue
            applicant.wealth = max(0.0, applicant.wealth - applicant.chronic_daily_cost)
            applicant.free_time = clamp(
                applicant.free_time - applicant.chronic_free_time_penalty,
                0.05,
                0.95,
            )

    def _reset_daily_counters(self) -> None:
        self._applications_today = 0
        self._hires_today = 0
        self._boost_spend_today = 0.0
        self._currency_purchased_today = 0.0
        self._quest_currency_today = 0.0

        for applicant in self.applicants:
            applicant.daily_applies = 0
            applicant.daily_messages = 0
            applicant.practiced_skills_today.clear()
            applicant.preparation_bonus = max(1.0, applicant.preparation_bonus * 0.96)
            if applicant.status == EmploymentStatus.UNEMPLOYED:
                applicant.cumulative_days_unemployed += 1
            if applicant.status == EmploymentStatus.EMPLOYED:
                for skill in applicant.current_role_skills:
                    applicant.practiced_skills_today.add(skill)

    def _update_market_state(self) -> None:
        shock = self.rng.uniform(-0.08, 0.08)
        self.market.job_market_index = clamp(self.market.job_market_index + shock, 0.55, 1.65)

        if self.market.job_market_index < 0.85:
            self.market.market_regime = "cold"
        elif self.market.job_market_index > 1.2:
            self.market.market_regime = "hot"
        else:
            self.market.market_regime = "neutral"

    def _expire_and_refresh_jobs(self) -> None:
        remaining_jobs: list[JobPosting] = []
        for job in self.jobs:
            if job.filled_by is not None:
                continue
            job.days_remaining -= 1
            if job.days_remaining > 0:
                remaining_jobs.append(job)
        self.jobs = remaining_jobs

        jobs_today = int(
            self.config.base_jobs_per_day
            * self.market.job_market_index
            * self.rng.uniform(0.70, 1.25)
        )
        for _ in range(max(1, jobs_today)):
            self.jobs.append(self._create_random_job())

    def _run_applicant_day(self, day: int, applicant: Applicant) -> None:
        if applicant.unavailable_days > 0:
            applicant.unavailable_days -= 1
            self._log_trace(applicant, day, "unavailable due to event")
            self._award_quests(applicant)
            return

        actions = self._action_budget(applicant)
        for _ in range(actions):
            action = self._pick_action(applicant)
            self._execute_action(day, applicant, action)

        self._award_quests(applicant)

    def _action_budget(self, applicant: Applicant) -> int:
        employed_penalty = 0.70 if applicant.status == EmploymentStatus.EMPLOYED else 1.10
        raw = 1.0 + 4.0 * applicant.engagement * applicant.free_time * employed_penalty
        return max(1, int(round(raw)))

    def _pick_action(self, applicant: Applicant) -> str:
        weights = {
            "apply": 0.36,
            "message_recruiter": 0.10,
            "prepare": 0.14,
            "learn_skill": 0.15,
            "side_gig": 0.10,
            "waste_time": 0.10,
            "gamble": 0.05,
        }

        if applicant.recent_rejections >= 4:
            weights["learn_skill"] += 0.12
            weights["prepare"] += 0.08
            weights["apply"] -= 0.08

        if applicant.wealth < 400:
            weights["side_gig"] += 0.15
            weights["gamble"] -= 0.03

        if applicant.status == EmploymentStatus.EMPLOYED:
            weights["apply"] -= 0.06
            weights["message_recruiter"] += 0.03

        total = sum(max(0.01, v) for v in weights.values())
        draw = self.rng.uniform(0.0, total)
        running = 0.0
        for action, weight in weights.items():
            running += max(0.01, weight)
            if draw <= running:
                return action
        return "waste_time"

    def _effective_strategy(self, applicant: Applicant) -> Strategy:
        if applicant.status == EmploymentStatus.UNEMPLOYED:
            return applicant.strategy

        # Employed users with stronger roles trend toward reach behavior;
        # lower-tier or lower-paid roles trend toward safer balanced behavior.
        if applicant.current_company_tier >= 4 or applicant.current_salary >= 130000:
            return Strategy.REACH
        if applicant.current_company_tier <= 2 or applicant.current_salary < 70000:
            return Strategy.BALANCED
        return applicant.strategy

    def _job_application_score(self, applicant: Applicant, job: JobPosting, strategy: Strategy) -> float:
        skill_match = self._skill_match(applicant, job)
        salary_norm = clamp(job.salary / 200000.0, 0.0, 1.0)
        tier_norm = clamp((job.tier - 1) / 4.0, 0.0, 1.0)
        competition = len(job.applicants)
        competition_penalty = 1.0 / (1.0 + 0.12 * competition)

        if strategy == Strategy.REACH:
            return (
                0.48 * salary_norm
                + 0.32 * tier_norm
                + 0.20 * skill_match
            ) * competition_penalty

        if strategy == Strategy.SAFETY:
            safety_bonus = 1.0 - 0.45 * tier_norm
            return (
                0.55 * skill_match
                + 0.25 * salary_norm
                + 0.20 * safety_bonus
            ) * competition_penalty

        # Balanced search: prefer strong matches with reasonable pay and lighter competition.
        balance_bonus = 1.0 - 0.20 * abs(tier_norm - 0.50)
        return (
            0.50 * skill_match
            + 0.30 * salary_norm
            + 0.20 * balance_bonus
        ) * competition_penalty

    def _execute_action(self, day: int, applicant: Applicant, action: str) -> None:
        if action == "apply":
            did_apply = self._submit_application(day, applicant)
            if did_apply:
                applicant.daily_applies += 1
                applicant.total_applications += 1
                self._applications_today += 1
                return

        if action == "message_recruiter":
            applicant.daily_messages += 1
            applicant.engagement = clamp(applicant.engagement + 0.005, 0.05, 1.0)
            self._log_trace(applicant, day, "messaged recruiter")
            return

        if action == "prepare":
            applicant.preparation_bonus = clamp(applicant.preparation_bonus * 1.03, 1.0, 1.35)
            self._log_trace(applicant, day, "interview prep done")
            return

        if action == "learn_skill":
            weakest = min(applicant.skills, key=applicant.skills.get)
            gain = self._skill_gain_amount(applicant, weakest)
            applicant.skills[weakest] = clamp(applicant.skills[weakest] + gain, 0.0, self._skill_cap(applicant))
            applicant.practiced_skills_today.add(weakest)
            applicant.experience = clamp(applicant.experience + 0.003 + 0.004 * applicant.intelligence, 0.0, 1.0)
            self._log_trace(applicant, day, f"skill training in {weakest} (+{gain:.4f})")
            return

        if action == "side_gig":
            gain = self.rng.uniform(8.0, 42.0)
            applicant.wealth += gain
            self._log_trace(applicant, day, f"side gig earned ${gain:.2f}")
            return

        if action == "gamble":
            outcome = self.rng.uniform(-120.0, 90.0)
            applicant.wealth = max(0.0, applicant.wealth + outcome)
            self._log_trace(applicant, day, f"gamble outcome ${outcome:.2f}")
            return

        self._log_trace(applicant, day, "wasted time")

    def _candidate_jobs_for(self, applicant: Applicant, strategy: Strategy) -> list[JobPosting]:
        open_jobs = [
            job
            for job in self.jobs
            if job.filled_by is None and job.id not in applicant.applied_job_ids
        ]
        if not open_jobs:
            return []

        if applicant.status == EmploymentStatus.EMPLOYED:
            # Employed users should not apply to obvious downgrades.
            min_tier = max(1, applicant.current_company_tier)
            min_salary = applicant.current_salary * 1.03
            open_jobs = [
                job
                for job in open_jobs
                if job.tier >= min_tier and job.salary >= min_salary
            ]
            if not open_jobs:
                return []

        if strategy == Strategy.REACH:
            return [j for j in open_jobs if j.tier >= 3] or open_jobs
        if strategy == Strategy.SAFETY:
            return [j for j in open_jobs if j.tier <= 3] or open_jobs
        return open_jobs

    def _submit_application(self, day: int, applicant: Applicant) -> bool:
        effective_strategy = self._effective_strategy(applicant)
        candidates = self._candidate_jobs_for(applicant, effective_strategy)
        if not candidates:
            return False

        job = max(
            candidates,
            key=lambda candidate: self._job_application_score(applicant, candidate, effective_strategy),
        )

        boost_multiplier = 1.0
        use_boost = self._should_boost(applicant, job, effective_strategy)
        if use_boost:
            boost_multiplier = self._buy_and_apply_boost(day, applicant, job)

        submission = ApplicationSubmission(
            applicant_id=applicant.id,
            boost_multiplier=boost_multiplier,
            prep_level=applicant.preparation_bonus,
        )
        job.applicants.append(submission)
        applicant.applied_job_ids.add(job.id)
        company_name = self._company_name(job.company_id)
        self.companies[job.company_id - 1].applications_received += 1
        self.interaction_events.append({
            "day": day, "applicant_id": applicant.id,
            "company_id": job.company_id, "company_name": company_name,
            "company_tier": job.tier, "event": "applied",
        })
        self._log_trace(
            applicant,
            day,
            (
                f"applied to job {job.id} at {company_name} "
                f"(tier {job.tier}, salary ${job.salary:.0f}, applicants now {len(job.applicants)})"
            ),
        )
        return True

    def _should_boost(self, applicant: Applicant, job: JobPosting, strategy: Strategy) -> bool:
        if self.fair_mode:
            return False
        
        # Calculate expected daily expense (baseline, no randomness)
        if applicant.status == EmploymentStatus.EMPLOYED:
            base_expense = self.config.base_daily_living_cost + self.config.base_daily_housing_cost
            tier_factor = 0.8 + 0.3 * (applicant.current_company_tier / 5.0)
            expected_daily_expense = base_expense * tier_factor
        else:
            base_expense = self.config.base_daily_living_cost + self.config.base_daily_housing_cost
            expected_daily_expense = base_expense * self.config.unemployed_expense_factor
        
        # Calculate days of runway
        days_of_runway = applicant.wealth / max(0.1, expected_daily_expense)
        
        # Adjust boost pressure based on financial runway
        if days_of_runway < 5:
            # Critical: almost no boost spending
            return self.rng.random() < 0.02
        if days_of_runway < 15:
            # Low: reduce pressure by 60%
            base_pressure = 0.35 * applicant.spending_willingness * 0.4
        elif days_of_runway < 30:
            # Medium-low: reduce pressure by 20%
            base_pressure = 0.35 * applicant.spending_willingness * 0.8
        else:
            # Comfortable: normal pressure
            base_pressure = 0.35 * applicant.spending_willingness
        
        pressure = base_pressure
        if strategy == Strategy.REACH and job.tier >= 4:
            pressure += 0.25
        if len(job.applicants) >= 8:
            pressure += 0.15
        if applicant.status == EmploymentStatus.UNEMPLOYED and applicant.recent_rejections >= 5:
            pressure += 0.18
        return self.rng.random() < clamp(pressure, 0.0, 0.92)

    def _boost_cost(self, job: JobPosting) -> float:
        tier_multiplier = 1.0 + 0.35 * (job.tier - 1)
        competition_multiplier = 1.0 + 0.08 * min(25, len(job.applicants))
        return self.config.base_boost_cost * tier_multiplier * competition_multiplier

    def _buy_and_apply_boost(self, day: int, applicant: Applicant, job: JobPosting) -> float:
        cost = self._boost_cost(job)

        if applicant.premium_currency < cost:
            deficit = cost - applicant.premium_currency
            usd_needed = deficit / self.config.premium_per_dollar
            purchase_usd = usd_needed * self.rng.uniform(1.05, 1.40)
            can_buy = purchase_usd <= applicant.wealth and self.rng.random() < applicant.spending_willingness
            if can_buy:
                purchased_currency = purchase_usd * self.config.premium_per_dollar
                applicant.wealth -= purchase_usd
                applicant.premium_currency += purchased_currency
                applicant.total_currency_purchased += purchased_currency
                self._currency_purchased_today += purchased_currency
                self._log_trace(applicant, day, f"bought {purchased_currency:.2f} premium for ${purchase_usd:.2f}")

        if applicant.premium_currency < cost:
            return 1.0

        applicant.premium_currency -= cost
        applicant.total_spent_on_boosts += cost
        self._boost_spend_today += cost

        company = self.companies[job.company_id - 1]
        company_share = cost * self.config.company_revenue_share
        company.boost_revenue += company_share

        multiplier = 1.0 + 0.18 * math.log1p(cost / self.config.base_boost_cost)
        self._log_trace(applicant, day, f"used boost costing {cost:.2f} (x{multiplier:.2f})")
        return clamp(multiplier, 1.0, 1.8)

    def _skill_match(self, applicant: Applicant, job: JobPosting) -> float:
        total = 0.0
        denom = 0.0
        for skill, req_weight in job.required_skills.items():
            total += applicant.skills.get(skill, 0.0) * req_weight
            denom += req_weight
        if denom <= 0:
            return 0.0
        return clamp(total / denom, 0.0, 1.0)

    def _skill_cap(self, applicant: Applicant) -> float:
        return clamp(0.92 + 0.04 * applicant.intelligence, 0.90, 0.97)

    def _skill_gain_amount(self, applicant: Applicant, skill: str) -> float:
        current = applicant.skills.get(skill, 0.0)
        cap = self._skill_cap(applicant)
        if current >= cap:
            return 0.0
        headroom = max(0.0, 1.0 - (current / cap))
        return (0.0035 + 0.0035 * applicant.intelligence) * (headroom ** 1.8)

    def _apply_skill_maintenance(self) -> None:
        for applicant in self.applicants:
            cap = self._skill_cap(applicant)
            for skill in ALL_SKILLS:
                if skill in applicant.practiced_skills_today:
                    applicant.skill_inactive_days[skill] = 0
                    if applicant.status == EmploymentStatus.EMPLOYED and skill in applicant.current_role_skills:
                        current = applicant.skills.get(skill, 0.0)
                        headroom = max(0.0, 1.0 - (current / cap))
                        passive_gain = (0.0009 + 0.0012 * applicant.intelligence) * (headroom ** 2.0)
                        applicant.skills[skill] = clamp(current + passive_gain, 0.0, cap)
                    continue

                applicant.skill_inactive_days[skill] = applicant.skill_inactive_days.get(skill, 0) + 1
                inactive = applicant.skill_inactive_days[skill]
                if inactive <= 6:
                    continue

                current = applicant.skills.get(skill, 0.0)
                floor = 0.10
                decay = (0.0012 + 0.0015 * max(0.0, current - 0.45)) * (1.0 + 0.03 * min(20, inactive - 6))
                applicant.skills[skill] = max(floor, current - decay)

    def _process_hiring(self, day: int) -> None:
        for job in self.jobs:
            pending_submissions = [submission for submission in job.applicants if submission.status == "pending"]
            if job.filled_by is not None or not pending_submissions:
                continue

            finalists: list[tuple[int, float, ApplicationSubmission]] = []
            competition = max(1, len(pending_submissions))
            competition_penalty = 1.0 + 0.025 * (competition - 1)

            for submission in pending_submissions:
                applicant = self.applicants[submission.applicant_id]
                skill_match = self._skill_match(applicant, job)
                experience_factor = 0.75 + 0.6 * applicant.experience
                nepotism_factor = 1.75 if applicant.nepotism_company_id == job.company_id else 1.0

                screen_prob = self.config.base_screen_rate
                screen_prob *= (0.30 + 1.6 * skill_match)
                screen_prob *= experience_factor
                screen_prob *= submission.boost_multiplier
                screen_prob *= nepotism_factor
                screen_prob *= self.market.job_market_index
                screen_prob /= competition_penalty
                screen_prob = clamp(screen_prob, 0.0005, 0.45)

                if self.rng.random() > screen_prob:
                    applicant.recent_rejections += 1
                    submission.status = "screen_reject"
                    self._log_trace(
                        applicant,
                        day,
                        f"job {job.id} at {self._company_name(job.company_id)}: resume screen reject",
                    )
                    continue

                interview_prob = self.config.base_interview_rate
                interview_prob *= (0.55 + 0.8 * applicant.charisma)
                interview_prob *= (0.55 + 0.7 * applicant.intelligence)
                interview_prob *= submission.prep_level
                interview_prob = clamp(interview_prob, 0.01, 0.85)

                if self.rng.random() <= interview_prob:
                    score = screen_prob * interview_prob * self.rng.uniform(0.85, 1.15)
                    finalists.append((applicant.id, score, submission))
                    self._log_trace(
                        applicant,
                        day,
                        f"job {job.id} at {self._company_name(job.company_id)}: interview passed",
                    )
                else:
                    applicant.recent_rejections += 1
                    submission.status = "interview_reject"
                    self._log_trace(
                        applicant,
                        day,
                        f"job {job.id} at {self._company_name(job.company_id)}: interview failed",
                    )

            if not finalists:
                continue

            winner_id, _, winner_submission = max(finalists, key=lambda item: item[1])
            winner = self.applicants[winner_id]
            accepted = self._accept_offer(winner, job)

            for submission in pending_submissions:
                if submission.applicant_id != winner_id:
                    other = self.applicants[submission.applicant_id]
                    other.recent_rejections += 1
                    submission.status = "final_reject"
                    self._log_trace(
                        other,
                        day,
                        f"job {job.id} at {self._company_name(job.company_id)}: not selected",
                    )

            if accepted:
                job.filled_by = winner_id
                winner_submission.status = "hired"
                self._hires_today += 1
                self.companies[job.company_id - 1].jobs_filled += 1
                self.interaction_events.append({
                    "day": day, "applicant_id": winner_id,
                    "company_id": job.company_id,
                    "company_name": self._company_name(job.company_id),
                    "company_tier": job.tier, "event": "hired",
                })
                self._log_trace(
                    winner,
                    day,
                    (
                        f"offer accepted: {self._company_name(job.company_id)} "
                        f"tier {job.tier} salary ${job.salary:.0f}"
                    ),
                )
            else:
                winner.recent_rejections += 1
                winner_submission.status = "offer_declined"
                self._log_trace(
                    winner,
                    day,
                    f"offer declined: {self._company_name(job.company_id)} job {job.id}",
                )

    def _accept_offer(self, applicant: Applicant, job: JobPosting) -> bool:
        if applicant.status == EmploymentStatus.UNEMPLOYED:
            accept = True
        else:
            salary_gain = job.salary > applicant.current_salary * 1.10
            tier_gain = job.tier > applicant.current_company_tier
            if applicant.strategy == Strategy.REACH:
                accept = tier_gain or salary_gain
            elif applicant.strategy == Strategy.SAFETY:
                accept = salary_gain and job.tier >= applicant.current_company_tier
            else:
                accept = tier_gain or salary_gain

        if not accept:
            return False

        applicant.status = EmploymentStatus.EMPLOYED
        applicant.current_company_id = job.company_id
        applicant.current_company_tier = job.tier
        applicant.current_salary = job.salary
        applicant.current_role_skills = list(job.required_skills.keys())
        for skill in applicant.current_role_skills:
            applicant.practiced_skills_today.add(skill)
            applicant.skill_inactive_days[skill] = 0
        applicant.hired_count += 1
        applicant.recent_rejections = 0
        return True

    def _award_quests(self, applicant: Applicant) -> None:
        reward = 0.0
        if applicant.daily_applies >= self.config.quest_apply_target:
            reward += self.config.quest_reward_currency * 0.65
        if applicant.daily_messages >= self.config.quest_message_target:
            reward += self.config.quest_reward_currency * 0.35

        if reward > 0.0:
            applicant.premium_currency += reward
            applicant.total_currency_earned_from_quests += reward
            self._quest_currency_today += reward

    def _apply_random_events(self, day: int) -> None:
        if self.rng.random() < self.config.mass_layoff_daily_prob:
            target_company = self.rng.choice(self.companies)
            laid_off = 0
            share = self.rng.uniform(0.10, 0.35)
            for applicant in self.applicants:
                if applicant.current_company_id == target_company.id and self.rng.random() < share:
                    laid_off_cid = applicant.current_company_id
                    applicant.status = EmploymentStatus.UNEMPLOYED
                    applicant.current_company_id = None
                    applicant.current_company_tier = 0
                    applicant.current_salary = 0.0
                    applicant.current_role_skills = []
                    laid_off += 1
                    self._log_trace(applicant, day, f"mass layoff from company {target_company.id}")
                    self.interaction_events.append({
                        "day": day, "applicant_id": applicant.id,
                        "company_id": laid_off_cid,
                        "company_name": self._company_name(laid_off_cid),
                        "company_tier": target_company.tier, "event": "laid_off",
                    })
            if laid_off > 0:
                self._total_mass_layoffs += 1
                self._total_affected_by_mass_layoff += laid_off
                self.market.job_market_index = clamp(self.market.job_market_index - 0.06, 0.55, 1.65)

        for applicant in self.applicants:
            if (not applicant.chronic_condition) and self.rng.random() < self.config.chronic_condition_daily_prob:
                self._activate_chronic_condition(applicant, day, "random")

            if self.rng.random() < self.config.accident_daily_prob:
                self._total_accidents += 1
                severe = self.rng.random() < self.config.accident_severe_prob
                if severe:
                    self._total_severe_accidents += 1
                    down_days = self.rng.randint(5, 14)
                    debt = self.rng.uniform(
                        self.config.accident_severe_cost_min,
                        self.config.accident_severe_cost_max,
                    )
                    self._activate_chronic_condition(applicant, day, "severe accident")
                else:
                    down_days = self.rng.randint(2, 7)
                    debt = self.rng.uniform(100.0, 2200.0)
                applicant.unavailable_days += down_days
                applicant.wealth = max(0.0, applicant.wealth - debt)
                severity_label = "severe" if severe else "standard"
                self._log_trace(
                    applicant,
                    day,
                    f"{severity_label} accident, unavailable {down_days} days and debt ${debt:.2f}",
                )

            if self.rng.random() < self.config.breakdown_daily_prob:
                self._total_breakdowns += 1
                cost = self.rng.uniform(self.config.breakdown_cost_min, self.config.breakdown_cost_max)
                applicant.wealth = max(0.0, applicant.wealth - cost)
                self._log_trace(applicant, day, f"breakdown event, cost ${cost:.2f}")

            if applicant.status == EmploymentStatus.EMPLOYED and self.rng.random() < self.config.fired_daily_prob:
                fired_cid = applicant.current_company_id
                fired_tier = applicant.current_company_tier
                self._total_firings += 1
                applicant.status = EmploymentStatus.UNEMPLOYED
                applicant.current_company_id = None
                applicant.current_company_tier = 0
                applicant.current_salary = 0.0
                applicant.current_role_skills = []
                self._log_trace(applicant, day, "fired from job")
                self.interaction_events.append({
                    "day": day, "applicant_id": applicant.id,
                    "company_id": fired_cid or -1,
                    "company_name": self._company_name(fired_cid) if fired_cid else "",
                    "company_tier": fired_tier, "event": "fired",
                })

            if self.rng.random() < self.config.windfall_daily_prob:
                self._total_windfalls += 1
                payout = self.rng.uniform(400.0, 9000.0)
                applicant.wealth += payout
                self._log_trace(applicant, day, f"positive windfall +${payout:.2f}")

    def _adapt_strategies(self) -> None:
        for applicant in self.applicants:
            if applicant.recent_rejections >= 5:
                if applicant.strategy == Strategy.REACH:
                    applicant.strategy = Strategy.BALANCED
                elif applicant.strategy == Strategy.BALANCED:
                    applicant.strategy = Strategy.SAFETY
                applicant.engagement = clamp(applicant.engagement + 0.01, 0.05, 1.0)

            if applicant.recent_rejections <= 1 and applicant.status == EmploymentStatus.EMPLOYED:
                applicant.engagement = clamp(applicant.engagement - 0.01, 0.05, 1.0)

            if applicant.status == EmploymentStatus.EMPLOYED:
                tier_target = {1: 0.55, 2: 0.50, 3: 0.45, 4: 0.38, 5: 0.32}.get(applicant.current_company_tier, 0.45)
                applicant.free_time = clamp(applicant.free_time + 0.08 * (tier_target - applicant.free_time), 0.08, 0.95)
            else:
                applicant.free_time = clamp(applicant.free_time + 0.05 * (0.62 - applicant.free_time), 0.08, 0.95)

            if applicant.wealth < 250.0:
                applicant.free_time = clamp(applicant.free_time - 0.01, 0.08, 0.95)

    def _collect_metrics(self, day: int) -> dict[str, float | int | str]:
        employed = [a for a in self.applicants if a.status == EmploymentStatus.EMPLOYED]
        open_jobs = sum(1 for j in self.jobs if j.filled_by is None)

        company_revenue_cumulative = sum(c.boost_revenue for c in self.companies)
        platform_revenue_cumulative = sum(a.total_spent_on_boosts for a in self.applicants) - company_revenue_cumulative

        avg_salary = 0.0
        if employed:
            avg_salary = sum(a.current_salary for a in employed) / len(employed)

        avg_quality_tier = 0.0
        if employed:
            avg_quality_tier = sum(a.current_company_tier for a in employed) / len(employed)

        metrics: dict[str, float | int | str] = {
            "day": day,
            "market_regime": self.market.market_regime,
            "market_index": round(self.market.job_market_index, 4),
            "employment_rate": len(employed) / len(self.applicants),
            "avg_salary": round(avg_salary, 2),
            "avg_company_tier": round(avg_quality_tier, 3),
            "open_jobs": open_jobs,
            "applications_today": self._applications_today,
            "hires_today": self._hires_today,
            "boost_spend_today": round(self._boost_spend_today, 2),
            "currency_purchased_today": round(self._currency_purchased_today, 2),
            "quest_currency_today": round(self._quest_currency_today, 2),
            "company_boost_revenue_cumulative": round(company_revenue_cumulative, 2),
            "platform_boost_revenue_cumulative": round(platform_revenue_cumulative, 2),
        }
        return metrics

    def _collect_applicant_snapshots(self, day: int) -> None:
        for a in self.applicants:
            self.applicant_snapshots.append(
                {
                    "day": day,
                    "applicant_id": a.id,
                    "status": a.status.value,
                    "company_id": a.current_company_id if a.current_company_id is not None else -1,
                    "company_name": self._company_name(a.current_company_id) if a.current_company_id else "",
                    "company_tier": a.current_company_tier,
                    "salary": round(a.current_salary, 2),
                    "strategy": a.strategy.value,
                    "wealth": round(a.wealth, 2),
                    "experience": round(a.experience, 4),
                    "recent_rejections": a.recent_rejections,
                    "hired_count": a.hired_count,
                    "total_applications": a.total_applications,
                    "total_spent_on_boosts": round(a.total_spent_on_boosts, 2),
                }
            )

    def final_summary(self) -> dict[str, float | int]:
        employed = [a for a in self.applicants if a.status == EmploymentStatus.EMPLOYED]
        placement_rate = len(employed) / len(self.applicants)
        average_tier = sum(a.current_company_tier for a in employed) / len(employed) if employed else 0.0
        total_spent = sum(a.total_spent_on_boosts for a in self.applicants)
        total_quest = sum(a.total_currency_earned_from_quests for a in self.applicants)
        total_purchased = sum(a.total_currency_purchased for a in self.applicants)
        avg_unemployment_days = sum(a.cumulative_days_unemployed for a in self.applicants) / len(self.applicants)

        # Balanced objective in [0, 1] combining outcomes and monetization.
        quality_component = clamp(average_tier / 5.0, 0.0, 1.0)
        placement_component = clamp(placement_rate, 0.0, 1.0)
        monetization_component = clamp(total_spent / max(1.0, len(self.applicants) * 75.0), 0.0, 1.0)
        balanced_score = 0.45 * placement_component + 0.35 * quality_component + 0.20 * monetization_component

        return {
            "num_users": len(self.applicants),
            "num_days": self.config.num_days,
            "placement_rate": round(placement_rate, 4),
            "average_company_tier": round(average_tier, 4),
            "total_boost_spend": round(total_spent, 2),
            "total_company_revenue": round(sum(c.boost_revenue for c in self.companies), 2),
            "total_platform_revenue": round(total_spent - sum(c.boost_revenue for c in self.companies), 2),
            "total_currency_from_quests": round(total_quest, 2),
            "total_currency_purchased": round(total_purchased, 2),
            "average_unemployment_days": round(avg_unemployment_days, 2),
            "balanced_success_score": round(balanced_score, 4),
        }

    def final_summary_detailed(self) -> dict[str, object]:
        """Generate detailed summary with personal achievements and event statistics."""
        employed = [a for a in self.applicants if a.status == EmploymentStatus.EMPLOYED]
        placement_rate = len(employed) / len(self.applicants)
        average_tier = sum(a.current_company_tier for a in employed) / len(employed) if employed else 0.0
        
        # Calculate individual metrics
        salary_changes = []
        end_wealths = []
        tier_improvements = []
        
        for applicant in self.applicants:
            # Salary change from start (assuming initial salary is 0 if unemployed)
            if applicant.status == EmploymentStatus.EMPLOYED:
                salary_changes.append((applicant.id, applicant.current_salary))
            end_wealths.append((applicant.id, applicant.wealth))
            # Tier improvement: from base_experience tier to current tier
            initial_tier = max(1, int(1 + 4 * applicant.base_experience))
            final_tier = applicant.current_company_tier if applicant.status == EmploymentStatus.EMPLOYED else 0
            tier_improvements.append((applicant.id, final_tier - initial_tier))
        
        # Find extremes
        top_earner = max(salary_changes, key=lambda x: x[1]) if salary_changes else None
        richest = max(end_wealths, key=lambda x: x[1])
        biggest_tier_jump = max(tier_improvements, key=lambda x: x[1])
        
        # Distribution stats
        total_spent = sum(a.total_spent_on_boosts for a in self.applicants)
        total_quest = sum(a.total_currency_earned_from_quests for a in self.applicants)
        total_purchased = sum(a.total_currency_purchased for a in self.applicants)
        avg_unemployment_days = sum(a.cumulative_days_unemployed for a in self.applicants) / len(self.applicants)
        
        # Balanced score
        quality_component = clamp(average_tier / 5.0, 0.0, 1.0)
        placement_component = clamp(placement_rate, 0.0, 1.0)
        monetization_component = clamp(total_spent / max(1.0, len(self.applicants) * 75.0), 0.0, 1.0)
        balanced_score = 0.45 * placement_component + 0.35 * quality_component + 0.20 * monetization_component
        
        return {
            "summary": {
                "num_users": len(self.applicants),
                "num_days": self.config.num_days,
                "placement_rate": round(placement_rate, 4),
                "employed_count": len(employed),
                "unemployed_count": len(self.applicants) - len(employed),
                "average_company_tier": round(average_tier, 4),
                "average_unemployment_days": round(avg_unemployment_days, 2),
                "balanced_success_score": round(balanced_score, 4),
            },
            "economics": {
                "total_boost_spend": round(total_spent, 2),
                "total_company_revenue": round(sum(c.boost_revenue for c in self.companies), 2),
                "total_platform_revenue": round(total_spent - sum(c.boost_revenue for c in self.companies), 2),
                "total_currency_earned_quests": round(total_quest, 2),
                "total_currency_purchased": round(total_purchased, 2),
                "total_jobs_filled": sum(c.jobs_filled for c in self.companies),
                "total_applications": sum(c.applications_received for c in self.companies),
            },
            "rare_events": {
                "accidents": self._total_accidents,
                "severe_accidents": self._total_severe_accidents,
                "firings": self._total_firings,
                "windfalls": self._total_windfalls,
                "mass_layoffs": self._total_mass_layoffs,
                "people_affected_by_layoffs": self._total_affected_by_mass_layoff,
                "chronic_conditions": self._total_chronic_conditions,
                "breakdowns": self._total_breakdowns,
            },
            "individual_achievements": {
                "top_earner": {
                    "applicant_id": top_earner[0],
                    "salary": round(top_earner[1], 2),
                } if top_earner else None,
                "richest_person": {
                    "applicant_id": richest[0],
                    "final_wealth": round(richest[1], 2),
                },
                "biggest_tier_jump": {
                    "applicant_id": biggest_tier_jump[0],
                    "tier_improvement": biggest_tier_jump[1],
                },
            },
        }

    def company_breakdown(self) -> list[dict[str, float | int | str]]:
        current_employees_by_company: dict[int, int] = {company.id: 0 for company in self.companies}
        for applicant in self.applicants:
            if applicant.current_company_id is not None:
                current_employees_by_company[applicant.current_company_id] += 1

        open_jobs_by_company: dict[int, int] = {company.id: 0 for company in self.companies}
        for job in self.jobs:
            if job.filled_by is None:
                open_jobs_by_company[job.company_id] += 1

        rows: list[dict[str, float | int | str]] = []
        total_boost_revenue = sum(company.boost_revenue for company in self.companies)
        for company in sorted(self.companies, key=lambda c: (c.tier, c.name), reverse=True):
            revenue_share = company.boost_revenue / total_boost_revenue if total_boost_revenue > 0 else 0.0
            rows.append(
                {
                    "company_id": company.id,
                    "company_name": company.name,
                    "tier": company.tier,
                    "current_employees": current_employees_by_company[company.id],
                    "open_jobs": open_jobs_by_company[company.id],
                    "jobs_filled": company.jobs_filled,
                    "applications_received": company.applications_received,
                    "boost_revenue": round(company.boost_revenue, 2),
                    "boost_revenue_share": round(revenue_share, 4),
                }
            )
        return rows

    def get_applicant_trace(self, applicant_id: int) -> list[str]:
        if 0 <= applicant_id < len(self.applicants):
            return self.applicants[applicant_id].trace
        return []

    def get_applicant_day_trace(self, applicant_id: int, day: int) -> list[str]:
        if 0 <= applicant_id < len(self.applicants):
            return self.applicants[applicant_id].trace_by_day.get(day, [])
        return []

    def _log_trace(self, applicant: Applicant, day: int, message: str) -> None:
        if not self._trace_enabled or applicant.id != self._trace_applicant_id:
            return
        line = f"Day {day}: {message}"
        applicant.trace.append(line)
        applicant.trace_by_day.setdefault(day, []).append(message)

    def _log_daily_snapshot(self, applicant: Applicant, day: int) -> None:
        if not self._trace_enabled or applicant.id != self._trace_applicant_id:
            return

        current_snapshot = self._capture_snapshot(applicant)
        previous_snapshot = self._trace_previous_snapshot
        if previous_snapshot is None:
            previous_snapshot = self._trace_start_snapshot or current_snapshot

        self._trace_status_windows_by_day[day] = build_daily_status_window(
            self._trace_detail,
            day,
            current_snapshot,
            previous_snapshot,
            ALL_SKILLS,
        )
        self._trace_previous_snapshot = current_snapshot

    def _capture_snapshot(self, applicant: Applicant) -> dict[str, object]:
        company_str = self._company_name(applicant.current_company_id) if applicant.current_company_id else "None"
        return {
            "user_id": applicant.id,
            "fixed": {
                "charisma": applicant.charisma,
                "intelligence": applicant.intelligence,
                "base_experience": applicant.base_experience,
                "spending_willingness": applicant.spending_willingness,
                "nepotism_company": self._company_name(applicant.nepotism_company_id) if applicant.nepotism_company_id else "None",
            },
            "dynamic": {
                "status": applicant.status.value,
                "strategy": applicant.strategy.value,
                "company": company_str,
                "salary": applicant.current_salary,
                "wealth": applicant.wealth,
                "premium": applicant.premium_currency,
                "engagement": applicant.engagement,
                "free_time": applicant.free_time,
                "experience": applicant.experience,
                "prep": applicant.preparation_bonus,
                "recent_rejections": applicant.recent_rejections,
                "unavailable_days": applicant.unavailable_days,
                "daily_applies": applicant.daily_applies,
                "daily_messages": applicant.daily_messages,
            },
            "skills": {skill: applicant.skills.get(skill, 0.0) for skill in ALL_SKILLS},
        }

