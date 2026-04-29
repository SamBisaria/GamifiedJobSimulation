# Gamified Job Matching Simulation

This project simulates a gamified job-search platform with:
- Daily quests (apply/message goals)
- Premium currency earned or purchased
- Boosted applications with tier/competition-based pricing
- Two-stage hiring (screening + interview)
- Dynamic applicant behavior adaptation
- Rare random events (accidents, firing, mass layoffs, windfalls)

## Quick start

```bash
python main.py --users 100 --days 100 --seed 42 --mode batch
```

## Modes

- `batch`: no per-day output; outputs only with `--write-outputs`
- `dashboard`: print day-by-day summary in terminal
- `trace`: print one applicant journey day-by-day
- `all`: dashboard + trace (outputs only with `--write-outputs`)

## Fair Mode

Use `--fair-mode` to disable premium currency purchases and boosts:

```bash
python main.py --users 100 --days 100 --seed 42 --fair-mode
```

In fair mode:
- Applicants cannot buy or earn premium currency from quests
- Boost functionality is disabled (all applications have 1.0x boost multiplier)
- All hiring is purely skill/experience-based with no monetary advantage

This mode is useful for comparing baseline job-matching outcomes against the gamified (paid) version.

Trace detail levels:
- `concise` (default): only changed stats and skills each day, but always includes employment status and current company/job line.
- `full`: full stat window every day.

Example with trace:

```bash
python main.py --users 100 --days 30 --mode trace --trace-id 7
```

Example with full trace detail:

```bash
python main.py --users 100 --days 30 --mode trace --trace-id 7 --trace-detail full
```

Example comparing fair vs. gamified modes:

```bash
# Fair (no boosts)
python main.py --users 100 --days 100 --seed 42 --fair-mode --mode dashboard --write-outputs

# Gamified (with boosts)
python main.py --users 100 --days 100 --seed 42 --mode dashboard --write-outputs
```

## Outputs

The run writes files to `output/` when `--write-outputs` is set:
- `daily_metrics_*.csv`
- `summary_*.json`
- `metrics_plot_*.png` (only if matplotlib is installed)

## Main parameters

Edit defaults in `job_sim/config.py` or pass CLI args for:
- `--users`: number of applicants (default: 100)
- `--days`: number of simulation days (default: 100)
- `--seed`: random seed for reproducibility (default: 42)
- `--fair-mode`: disable premium currency and boosts (default: off)
- `--start-unemployed`: start all applicants unemployed (default: off)
