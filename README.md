# Gamified Job Matching Simulation

An agent-based simulation of a job-search platform that models gamification mechanics (premium currency, boosts, daily quests) and their effect on labor market outcomes. Supports multiple simulation modes for comparing gamified vs. fair vs. mixed-adoption scenarios, and generates animated HTML visualizations from run outputs.

## Project structure

```
main.py                   # CLI entry point for running simulations
animate.py                # CLI entry point for generating Plotly animations
job_sim/
  config.py               # SimulationConfig dataclass with all tunable parameters
  models.py               # Core data models (Applicant, Company, JobPosting, etc.)
  simulation.py           # Main simulation engine (JobMarketSimulation)
  trace.py                # Per-applicant daily trace formatting
  visualization.py        # CSV/JSON output writers and basic matplotlib plots
output/                   # Generated run outputs (CSVs, JSONs, HTML animations)
```

## Quick start

```bash
python main.py --users 100 --days 100 --seed 42 --mode batch
```

## Simulation modes

| Mode | Description |
|---|---|
| `batch` | No per-day output; write files only if `--write-outputs` is set |
| `dashboard` | Print a day-by-day summary table to the terminal |
| `trace` | Print one applicant's full journey day-by-day |
| `all` | `dashboard` + `trace` combined |

## Competition modes

### Gamified (default)
Applicants earn premium currency by completing daily quests (apply / message goals) and can purchase additional currency to boost their applications. Boosted applications receive a multiplier that increases their screening probability.

### Fair mode (`--fair-mode`)
Disables premium currency purchases and boosts entirely. All applications receive a 1.0× multiplier; hiring is purely skill- and experience-based. Useful as a baseline to compare against the gamified version.

```bash
python main.py --users 100 --days 100 --seed 42 --fair-mode --mode dashboard --write-outputs
```

### Mixed mode (`--mixed-mode`)
A fraction of the population (`--platform-adoption-rate`, default 0.5) uses the gamified platform while the rest do not. Allows studying partial-adoption dynamics.

```bash
python main.py --users 1000 --days 100 --mixed-mode --platform-adoption-rate 0.10 --write-outputs
```

## CLI reference (`main.py`)

| Argument | Default | Description |
|---|---|---|
| `--users` | `100` | Number of applicants |
| `--days` | `100` | Simulation duration in days |
| `--seed` | `42` | Random seed for reproducibility |
| `--mode` | `batch` | Output mode (`batch`, `dashboard`, `trace`, `all`) |
| `--trace-id` | `0` | Applicant ID to follow in `trace`/`all` mode |
| `--trace-detail` | `concise` | Trace verbosity: `concise` (changed stats only) or `full` (full stat window every day) |
| `--output-dir` | `output/` | Directory for CSV/JSON/plot output |
| `--write-outputs` | off | Write output files when set |
| `--fair-mode` | off | Disable premium currency and boosts |
| `--start-unemployed` | off | Start all applicants unemployed |
| `--mixed-mode` | off | Split population into platform users and non-users |
| `--platform-adoption-rate` | `0.5` | Fraction of population on the platform (mixed mode only) |

## Simulation mechanics

### Applicants
Each applicant has fixed traits (charisma, intelligence, spending willingness, nepotism tie) and dynamic traits (wealth, experience, engagement, free time, skills). They choose one of three application strategies—`reach`, `balanced`, or `safety`—and adapt over time.

Skills tracked: `python`, `sql`, `ml`, `frontend`, `backend`, `cloud`, `devops`, `communication`.

### Companies & jobs
Companies are organized into five tiers (tier 5 = top firms like "Boogle", "Rainforest"; tier 1 = entry-level). New job postings arrive each day and expire after a configurable number of days. Hiring is a two-stage process: screening then interview.

### Gamification mechanics
- **Daily quests**: completing application and message goals rewards premium currency.
- **Boosts**: spending premium currency raises an application's screening multiplier.
- **Premium currency**: earned via quests or purchased with real wealth.

### Rare random events
Stochastic life events that affect applicant wealth and availability:
- Accidents (including severe accidents with large medical costs)
- Sudden firing
- Financial windfalls
- Mass layoffs (company-wide)
- Chronic health conditions (ongoing daily cost + free-time penalty)
- Mental health breakdowns (one-time wealth shock)

### Economy
Applicants pay daily living expenses (base costs + housing, scaled by wealth and employment status). Platform revenue is split between the company and the platform (`company_revenue_share`, default 65%).

## Trace mode

```bash
# Follow applicant #7 with concise output
python main.py --users 100 --days 30 --mode trace --trace-id 7

# Full stat window every day
python main.py --users 100 --days 30 --mode trace --trace-id 7 --trace-detail full
```

## Output files

When `--write-outputs` is set, the following files are written to `--output-dir`:

| File | Description |
|---|---|
| `daily_metrics_*.csv` | Per-day aggregate market metrics |
| `summary_*.json` | End-of-run summary statistics |
| `company_breakdown_*.csv` | Per-company hiring and revenue breakdown |
| `company_breakdown_*.json` | Same data in JSON format |
| `applicant_snapshots_*.csv` | Per-applicant per-day snapshots (used by `animate.py`) |
| `interaction_events_*.csv` | Log of all application and hiring events |
| `metrics_plot_*.png` | Basic matplotlib plot (requires `matplotlib`) |

## Animations (`animate.py`)

After a run with `--write-outputs`, generate interactive Plotly HTML animations:

```bash
python animate.py --output-dir output/my_run/

# Individual applicant journey
python animate.py --output-dir output/my_run/ --applicant-id 7

# Compare gamified run against a fair-mode run
python animate.py --output-dir output/gamified_run/ --fair-dir output/fair_run/
```

Animations produced:

| File | Description |
|---|---|
| `animation_population.html` | Stacked bar of applicant states (unemployed, tier 1–5) over time |
| `animation_population_with_individuals.html` | Same view with individual dot overlay |
| `animation_wealth_income.html` | Wealth and income scatter over time |
| `animation_applicant_0.html` | Individual applicant journey (wealth, skills, status) |
| `animation_interactions.html` | Application and hiring event stream |
| `animation_revenue.html` | Platform and company revenue over time |
| `animation_apps_vs_salary.html` | Applications received vs. salary by company tier |
| `animation_spend_vs_salary.html` | Boost spend vs. salary outcome |
| `animation_skills_spend_vs_salary.html` | Skill level + spend vs. salary |
| `animation_group_comparison.html` | Platform users vs. non-users (mixed mode) |

## Configuration

All simulation parameters are in `job_sim/config.py` (`SimulationConfig`). Key knobs:

| Parameter | Default | Description |
|---|---|---|
| `base_jobs_per_day` | `35` | New job postings created each day |
| `max_job_age_days` | `21` | Days before an unfilled posting expires |
| `initial_open_jobs` | `120` | Jobs open at simulation start |
| `starting_wealth_min/max` | `250 / 20000` | Applicant starting wealth range |
| `premium_per_dollar` | `8.0` | Premium currency per dollar spent |
| `base_boost_cost` | `10.0` | Base premium currency cost for one boost |
| `base_screen_rate` | `0.05` | Base probability of passing screening |
| `base_interview_rate` | `0.25` | Base probability of passing interview |
| `quest_apply_target` | `3` | Applications required to complete the daily quest |
| `quest_reward_currency` | `8.0` | Premium currency awarded for quest completion |
| `company_revenue_share` | `0.65` | Share of boost revenue paid to companies |
| `accident_daily_prob` | `0.00005` | Per-applicant daily accident probability |
| `fired_daily_prob` | `0.001` | Per-applicant daily firing probability |
| `mass_layoff_daily_prob` | `0.02` | Per-company daily mass-layoff probability |

## Example workflows

```bash
# Reproduce a specific run
python main.py --users 1000 --days 100 --seed 42 --mode batch --write-outputs

# Compare fair vs. gamified at scale
python main.py --users 1000 --days 100 --seed 42 --fair-mode --write-outputs --output-dir output/fair/
python main.py --users 1000 --days 100 --seed 42 --write-outputs --output-dir output/gamified/
python animate.py --output-dir output/gamified/ --fair-dir output/fair/

# Study low-adoption mixed mode, everyone starts unemployed
python main.py --users 1000 --days 100 --mixed-mode --platform-adoption-rate 0.10 \
    --start-unemployed --write-outputs
```
