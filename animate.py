from __future__ import annotations

import argparse
import glob
import os

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def latest_file(output_dir: str, pattern: str) -> str:
    matches = sorted(glob.glob(os.path.join(output_dir, pattern)))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} in {output_dir}")
    return matches[-1]


def make_population_animation(snapshots_path: str, output_dir: str) -> str:
    df = pd.read_csv(snapshots_path)
    # Map each person to a state label: unemployed, or tier-1..tier-5
    df["state"] = np.where(
        df["status"] == "unemployed",
        "unemployed",
        "tier-" + df["company_tier"].astype(int).astype(str),
    )
    days = sorted(df["day"].unique())
    state_order = ["unemployed", "tier-1", "tier-2", "tier-3", "tier-4", "tier-5"]
    colors = ["#d62728", "#aec7e8", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"]

    frames = []
    for day in days:
        day_df = df[df["day"] == day]
        counts = day_df["state"].value_counts()
        frames.append(
            go.Frame(
                data=[
                    go.Bar(
                        name=state,
                        x=["Population"],
                        y=[counts.get(state, 0)],
                        marker_color=color,
                    )
                    for state, color in zip(state_order, colors)
                ],
                name=str(day),
                layout=go.Layout(title_text=f"Day {day}"),
            )
        )

    # Build initial data from day 1
    day1 = df[df["day"] == days[0]]["state"].value_counts()
    fig = go.Figure(
        data=[
            go.Bar(name=s, x=["Population"], y=[day1.get(s, 0)], marker_color=c)
            for s, c in zip(state_order, colors)
        ],
        frames=frames,
        layout=go.Layout(
            title="Population State Distribution Over Time",
            barmode="stack",
            yaxis_title="Number of Applicants",
            updatemenus=[{
                "type": "buttons",
                "buttons": [
                    {"label": "Play", "method": "animate",
                     "args": [None, {"frame": {"duration": 120, "redraw": True}, "fromcurrent": True}]},
                    {"label": "Pause", "method": "animate",
                     "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]},
                ],
            }],
            sliders=[{
                "steps": [{"method": "animate", "args": [[str(d)], {"mode": "immediate"}], "label": str(d)} for d in days],
                "transition": {"duration": 80},
                "x": 0.1, "len": 0.9,
            }],
        ),
    )

    target = os.path.join(output_dir, "animation_population.html")
    fig.write_html(target)
    print(f"Population animation → {target}")
    return target

def make_population_animation_with_dots(snapshots_path: str, output_dir: str) -> str:
    df = pd.read_csv(snapshots_path)
    df["tier_val"] = np.where(df["status"] == "unemployed", 0, df["company_tier"].astype(int))
    df["state"] = np.where(
        df["status"] == "unemployed",
        "unemployed",
        "tier-" + df["company_tier"].astype(int).astype(str),
    )

    days = sorted(df["day"].unique())
    applicant_ids = sorted(df["applicant_id"].unique())
    n = len(applicant_ids)
    id_to_x = {aid: i for i, aid in enumerate(applicant_ids)}

    # Fixed Y jitter per applicant so dots at the same tier are visually spread
    rng_jitter = np.random.default_rng(42)
    y_jitter = {aid: rng_jitter.uniform(-0.28, 0.28) for aid in applicant_ids}

    state_order = ["unemployed", "tier-1", "tier-2", "tier-3", "tier-4", "tier-5"]
    tier_colors_list = ["#d62728", "#aec7e8", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"]
    state_to_color = dict(zip(state_order, tier_colors_list))

    x_dot = [id_to_x[aid] for aid in applicant_ids]

    def day_dot_data(day_df: pd.DataFrame):
        indexed = day_df.set_index("applicant_id")
        y_vals, colors, hovers = [], [], []
        for aid in applicant_ids:
            if aid in indexed.index:
                row = indexed.loc[aid]
                tv = int(row["tier_val"])
                state = str(row["state"])
                salary = float(row["salary"])
                wealth = float(row["wealth"])
            else:
                tv, state, salary, wealth = 0, "unemployed", 0.0, 0.0
            y_vals.append(tv + y_jitter[aid])
            colors.append(state_to_color.get(state, "#d62728"))
            hovers.append(
                f"ID: {aid}<br>State: {state}<br>Salary: ${salary:,.0f}<br>Wealth: ${wealth:,.0f}"
            )
        return y_vals, colors, hovers

    # Pre-build all frames
    frames = []
    for day in days:
        day_df = df[df["day"] == day]
        y_vals, colors, hovers = day_dot_data(day_df)
        counts = day_df["state"].value_counts()
        frames.append(go.Frame(
            data=[
                go.Scatter(
                    x=x_dot, y=y_vals, mode="markers",
                    marker=dict(color=colors, size=7, opacity=0.85),
                    text=hovers, hoverinfo="text",
                ),
                *[
                    go.Bar(x=["Population"], y=[counts.get(s, 0)], marker_color=c, name=s)
                    for s, c in zip(state_order, tier_colors_list)
                ],
            ],
            traces=list(range(7)),
            name=str(day),
            layout=go.Layout(title_text=f"Day {day}"),
        ))

    # Initial state (day 1)
    day1_df = df[df["day"] == days[0]]
    y_init, colors_init, hovers_init = day_dot_data(day1_df)
    counts_init = day1_df["state"].value_counts()

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.72, 0.28],
        subplot_titles=["Individual Applicants — each dot is one person", "Population Breakdown"],
    )

    fig.add_trace(
        go.Scatter(
            x=x_dot, y=y_init, mode="markers",
            marker=dict(color=colors_init, size=7, opacity=0.85),
            text=hovers_init, hoverinfo="text",
            name="Applicants", showlegend=False,
        ),
        row=1, col=1,
    )
    for state, color in zip(state_order, tier_colors_list):
        fig.add_trace(
            go.Bar(x=["Population"], y=[counts_init.get(state, 0)], marker_color=color, name=state),
            row=1, col=2,
        )

    fig.update_yaxes(
        tickvals=list(range(6)),
        ticktext=["Unemployed", "Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"],
        range=[-0.7, 5.7],
        row=1, col=1,
    )
    fig.update_xaxes(title_text="Applicant", showticklabels=False, range=[-1, n], row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    fig.frames = frames
    fig.update_layout(
        title="Job Market Simulation — Day 1",
        barmode="stack",
        height=580,
        updatemenus=[{
            "type": "buttons",
            "y": -0.12,
            "x": 0.5,
            "xanchor": "center",
            "buttons": [
                {"label": "▶ Play", "method": "animate",
                 "args": [None, {"frame": {"duration": 200, "redraw": True},
                                 "transition": {"duration": 120, "easing": "cubic-in-out"},
                                 "fromcurrent": True}]},
                {"label": "⏸ Pause", "method": "animate",
                 "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]},
            ],
        }],
        sliders=[{
            "steps": [
                {"method": "animate",
                 "args": [[str(d)], {"mode": "immediate",
                                     "transition": {"duration": 80, "easing": "cubic-in-out"},
                                     "frame": {"duration": 200, "redraw": True}}],
                 "label": str(d)}
                for d in days
            ],
            "x": 0.05, "len": 0.9,
            "currentvalue": {"prefix": "Day: ", "visible": True, "xanchor": "center"},
            "pad": {"t": 55},
        }],
    )

    target = os.path.join(output_dir, "animation_population_with_individuals.html")
    fig.write_html(target)
    print(f"Population animation → {target}")
    return target


def make_individual_animation(snapshots_path: str, daily_metrics_path: str, output_dir: str, applicant_id: int) -> str:
    df = pd.read_csv(snapshots_path)
    person = df[df["applicant_id"] == applicant_id].sort_values("day")
    if person.empty:
        raise ValueError(f"No data for applicant {applicant_id}")

    days = person["day"].tolist()
    # Encode status as numeric tier for color: 0 = unemployed
    tier_values = np.where(person["status"] == "unemployed", 0, person["company_tier"].astype(int)).tolist()

    frames = []
    for i, day in enumerate(days):
        frames.append(go.Frame(
            data=[
                go.Scatter(x=days[:i+1], y=tier_values[:i+1],
                           mode="lines+markers", name="Company Tier",
                           line=dict(color="#1f77b4"), yaxis="y1"),
                go.Scatter(x=days[:i+1], y=person["salary"].tolist()[:i+1],
                           mode="lines", name="Salary",
                           line=dict(color="#2ca02c"), yaxis="y2"),
                go.Scatter(x=days[:i+1], y=person["wealth"].tolist()[:i+1],
                           mode="lines", name="Wealth",
                           line=dict(color="#ff7f0e"), yaxis="y3"),
            ],
            name=str(day),
        ))

    fig = go.Figure(
        data=[
            go.Scatter(x=[], y=[], mode="lines+markers", name="Company Tier (0=unemployed)", yaxis="y1"),
            go.Scatter(x=[], y=[], mode="lines", name="Salary", yaxis="y2"),
            go.Scatter(x=[], y=[], mode="lines", name="Wealth", yaxis="y3"),
        ],
        frames=frames,
        layout=go.Layout(
            title=f"Applicant {applicant_id} Journey",
            xaxis=dict(title="Day", range=[min(days)-1, max(days)+1]),
            yaxis=dict(title="Tier", range=[-0.2, 5.5], domain=[0.68, 1.0]),
            yaxis2=dict(title="Salary ($)", domain=[0.34, 0.64]),
            yaxis3=dict(title="Wealth ($)", domain=[0.0, 0.30]),
            legend=dict(orientation="h"),
            updatemenus=[{
                "type": "buttons",
                "buttons": [
                    {"label": "Play", "method": "animate",
                     "args": [None, {"frame": {"duration": 100, "redraw": True}, "fromcurrent": True}]},
                    {"label": "Pause", "method": "animate",
                     "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]},
                ],
            }],
            sliders=[{
                "steps": [{"method": "animate", "args": [[str(d)], {"mode": "immediate"}], "label": str(d)} for d in days],
                "transition": {"duration": 50},
                "x": 0.1, "len": 0.9,
            }],
        ),
    )

    target = os.path.join(output_dir, f"animation_applicant_{applicant_id}.html")
    fig.write_html(target)
    print(f"Individual animation → {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate animations from simulation output")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--applicant-id", type=int, default=0, help="Applicant ID for individual journey animation")
    args = parser.parse_args()

    snapshots = latest_file(args.output_dir, "applicant_snapshots_*.csv")
    daily = latest_file(args.output_dir, "daily_metrics_*.csv")

    make_population_animation(snapshots, args.output_dir)
    make_population_animation_with_dots(snapshots, args.output_dir)
    make_individual_animation(snapshots, daily, args.output_dir, args.applicant_id)