from __future__ import annotations

import argparse
import glob
import os

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math


def latest_file(output_dir: str, pattern: str) -> str:
    matches = sorted(glob.glob(os.path.join(output_dir, pattern)))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} in {output_dir}")
    return matches[-1]


def make_population_animation(snapshots_path: str, daily_metrics_path: str, output_dir: str) -> str:
    df = pd.read_csv(snapshots_path)
    dm = pd.read_csv(daily_metrics_path).sort_values("day")
    cum_by_day = {
        int(r["day"]): (
            float(r["company_boost_revenue_cumulative"] + r["platform_boost_revenue_cumulative"]),
            float(r["platform_boost_revenue_cumulative"]),
        )
        for _, r in dm.iterrows()
    }
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
        cum_spend, cum_plat = cum_by_day.get(day, (0.0, 0.0))
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
                layout=go.Layout(title_text=(
                    f"Day {day}  |  Applicant Spend: ${cum_spend:,.0f}"
                    f"  |  Platform Revenue: ${cum_plat:,.0f}"
                )),
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

def make_population_animation_with_dots(snapshots_path: str, daily_metrics_path: str, output_dir: str) -> str:
    df = pd.read_csv(snapshots_path)
    dm = pd.read_csv(daily_metrics_path).sort_values("day")
    cum_by_day = {
        int(r["day"]): (
            float(r["company_boost_revenue_cumulative"] + r["platform_boost_revenue_cumulative"]),
            float(r["platform_boost_revenue_cumulative"]),
        )
        for _, r in dm.iterrows()
    }
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
        cum_spend, cum_plat = cum_by_day.get(day, (0.0, 0.0))
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
            layout=go.Layout(title_text=(
                    f"Day {day}  |  Applicant Spend: ${cum_spend:,.0f}"
                    f"  |  Platform Revenue: ${cum_plat:,.0f}"
                )),
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

def make_wealth_income_animation(snapshots_path: str, daily_metrics_path: str, output_dir: str) -> str:
    df = pd.read_csv(snapshots_path)
    dm = pd.read_csv(daily_metrics_path).sort_values("day")
    cum_by_day = {
        int(r["day"]): (
            float(r["company_boost_revenue_cumulative"] + r["platform_boost_revenue_cumulative"]),
            float(r["platform_boost_revenue_cumulative"]),
        )
        for _, r in dm.iterrows()
    }

    days = sorted(df["day"].unique())
    applicant_ids = sorted(df["applicant_id"].unique())

    # Color each person by their FINAL tier so you can see where trajectories end up
    last_day = days[-1]
    final_snap = df[df["day"] == last_day].set_index("applicant_id")
    tier_pal = {0: "#e84040", 1: "#90caf9", 2: "#42a5f5", 3: "#66bb6a", 4: "#ffa726", 5: "#ab47bc"}
    tier_labels = {0: "Unemployed", 1: "Tier 1", 2: "Tier 2", 3: "Tier 3", 4: "Tier 4", 5: "Tier 5"}

    def final_tier(aid: int) -> int:
        if aid in final_snap.index:
            r = final_snap.loc[aid]
            return 0 if str(r["status"]) == "unemployed" else int(r["company_tier"])
        return 0

    tier_groups: dict[int, list[int]] = {t: [] for t in range(6)}
    for aid in applicant_ids:
        tier_groups[final_tier(aid)].append(aid)

    # Pre-pivot: salary is None when unemployed (produces visible gaps in lines)
    salary_by_aid: dict[int, dict[int, float | None]] = {}
    wealth_by_aid: dict[int, dict[int, float]] = {}
    for aid in applicant_ids:
        pf = df[df["applicant_id"] == aid].sort_values("day")
        salary_by_aid[aid] = {
            int(r["day"]): (None if str(r["status"]) == "unemployed" else float(r["salary"]))
            for _, r in pf.iterrows()
        }
        wealth_by_aid[aid] = dict(zip(pf["day"].astype(int), pf["wealth"].astype(float)))

    # Average across employed only for salary, all for wealth
    avg_salary = df[df["status"] == "employed"].groupby("day")["salary"].mean()
    avg_wealth = df.groupby("day")["wealth"].mean()

    salary_max = float(df["salary"].max()) * 1.08
    wealth_max = float(df["wealth"].max()) * 1.08

    def concat_lines(tier: int, data_dict: dict[int, dict], days_up_to: list[int]):
        """Concatenate all lines for a tier group with None separators between people."""
        x_vals: list = []
        y_vals: list = []
        for aid in tier_groups[tier]:
            for d in days_up_to:
                x_vals.append(d)
                y_vals.append(data_dict[aid].get(d, None))
            x_vals.append(None)
            y_vals.append(None)
        return x_vals, y_vals

    def build_traces(days_up_to: list[int]) -> list:
        traces = []
        # Traces 0-5: salary per tier group
        for t in range(6):
            x, y = concat_lines(t, salary_by_aid, days_up_to)
            traces.append(go.Scatter(
                x=x, y=y, mode="lines",
                line=dict(color=tier_pal[t], width=0.8), opacity=0.3,
                showlegend=False, yaxis="y",
            ))
        # Trace 6: avg salary
        traces.append(go.Scatter(
            x=days_up_to,
            y=[avg_salary.get(d, None) for d in days_up_to],
            mode="lines", line=dict(color="white", width=2.5, dash="dot"),
            showlegend=False, yaxis="y",
        ))
        # Traces 7-12: wealth per tier group
        for t in range(6):
            x, y = concat_lines(t, wealth_by_aid, days_up_to)
            traces.append(go.Scatter(
                x=x, y=y, mode="lines",
                line=dict(color=tier_pal[t], width=0.8), opacity=0.3,
                showlegend=False, yaxis="y2",
            ))
        # Trace 13: avg wealth
        traces.append(go.Scatter(
            x=days_up_to,
            y=[avg_wealth.get(d, None) for d in days_up_to],
            mode="lines", line=dict(color="white", width=2.5, dash="dot"),
            showlegend=False, yaxis="y2",
        ))
        return traces
    
    frames = []
    for day in days:
        cum_spend, cum_plat = cum_by_day.get(day, (0.0, 0.0))
        frames.append(
            go.Frame(
                data=build_traces([d for d in days if d <= day]),
                traces=list(range(14)),
                name=str(day),
                layout=go.Layout(title_text=(
                        f"Day {day}  |  Applicant Spend: ${cum_spend:,.0f}"
                        f"  |  Platform Revenue: ${cum_plat:,.0f}"
                    )),
            )
        )

    fig = go.Figure(
        data=build_traces([days[0]]),
        frames=frames,
        layout=go.Layout(
            title="Income & Wealth Trajectories — All Applicants (color = final tier)",
            height=680,
            plot_bgcolor="#12122a",
            paper_bgcolor="#0d0d1f",
            font=dict(color="white"),
            # Two vertically stacked panels sharing the x-axis
            xaxis=dict(
                title="Day", range=[min(days) - 1, max(days) + 1],
                gridcolor="rgba(255,255,255,0.06)",
            ),
            yaxis=dict(
                title="Salary ($)", domain=[0.54, 1.0],
                range=[0, salary_max],
                gridcolor="rgba(255,255,255,0.06)",
            ),
            yaxis2=dict(
                title="Wealth ($)", domain=[0.0, 0.46],
                range=[0, wealth_max],
                gridcolor="rgba(255,255,255,0.06)",
                anchor="x",
            ),
            annotations=[
                dict(x=0.01, y=0.99, xref="paper", yref="paper",
                     text="<b>Salary</b> (gaps = unemployed)", showarrow=False,
                     font=dict(size=11, color="rgba(255,255,255,0.7)"), xanchor="left"),
                dict(x=0.01, y=0.46, xref="paper", yref="paper",
                     text="<b>Wealth</b>", showarrow=False,
                     font=dict(size=11, color="rgba(255,255,255,0.7)"), xanchor="left"),
                dict(x=0.99, y=0.99, xref="paper", yref="paper",
                     text="━ ┄ = average", showarrow=False,
                     font=dict(size=9, color="white"), xanchor="right"),
            ] + [
                dict(
                    x=1.01, y=0.96 - i * 0.07, xref="paper", yref="paper",
                    text=f"● {tier_labels[t]}", showarrow=False,
                    font=dict(size=9, color=tier_pal[t]), xanchor="left",
                )
                for i, t in enumerate(range(6)) if tier_groups[t]
            ],
            updatemenus=[{
                "type": "buttons",
                "y": -0.1, "x": 0.5, "xanchor": "center",
                "bgcolor": "#2a2a44",
                "buttons": [
                    {"label": "▶ Play", "method": "animate",
                     "args": [None, {"frame": {"duration": 150, "redraw": True},
                                     "transition": {"duration": 80, "easing": "cubic-in-out"},
                                     "fromcurrent": True}]},
                    {"label": "⏸ Pause", "method": "animate",
                     "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]},
                ],
            }],
            sliders=[{
                "steps": [
                    {"method": "animate",
                     "args": [[str(d)], {"mode": "immediate",
                                         "transition": {"duration": 60, "easing": "cubic-in-out"},
                                         "frame": {"duration": 150, "redraw": True}}],
                     "label": str(d)}
                    for d in days
                ],
                "x": 0.05, "len": 0.9,
                "bgcolor": "#2a2a44",
                "currentvalue": {"prefix": "Day: ", "visible": True, "font": {"color": "white"}},
                "pad": {"t": 50},
            }],
        ),
    )

    target = os.path.join(output_dir, "animation_wealth_income.html")
    fig.write_html(target)
    print(f"Wealth & income animation → {target}")
    return target


def make_individual_animation(snapshots_path: str, output_dir: str, applicant_id: int) -> str:
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

def make_interaction_animation(snapshots_path: str, events_path: str, daily_metrics_path: str, output_dir: str) -> str:
    df_snap = pd.read_csv(snapshots_path)
    df_ev = pd.read_csv(events_path)
    dm = pd.read_csv(daily_metrics_path).sort_values("day")
    cum_by_day = {
        int(r["day"]): (
            float(r["company_boost_revenue_cumulative"] + r["platform_boost_revenue_cumulative"]),
            float(r["platform_boost_revenue_cumulative"]),
        )
        for _, r in dm.iterrows()
    }

    days = sorted(df_snap["day"].unique())
    applicant_ids = sorted(df_snap["applicant_id"].unique())
    n = len(applicant_ids)

    # ── Applicant grid: left portion (10 cols) ───────────────────────────────
    grid_cols = 10
    grid_rows = math.ceil(n / grid_cols)
    aid_to_pos: dict[int, tuple[float, float]] = {}
    for i, aid in enumerate(applicant_ids):
        col = i % grid_cols
        row = i // grid_cols
        x = 0.03 + col * 0.034
        y = 0.95 - row * (0.88 / max(1, grid_rows - 1))
        aid_to_pos[aid] = (x, y)

    # ── Company column: right side, sorted tier desc then name ───────────────
    comp_df = (
        df_snap[df_snap["company_id"] > 0][["company_id", "company_name", "company_tier"]]
        .drop_duplicates("company_id")
        .sort_values(["company_tier", "company_name"], ascending=[False, True])
        .reset_index(drop=True)
    )
    companies = comp_df.to_dict("records")
    n_c = len(companies)
    cid_to_pos: dict[int, tuple[float, float]] = {}
    for i, c in enumerate(companies):
        cid_to_pos[c["company_id"]] = (0.82, 0.95 - i * (0.88 / max(1, n_c - 1)))

    tier_pal = {0: "#e84040", 1: "#90caf9", 2: "#42a5f5", 3: "#66bb6a", 4: "#ffa726", 5: "#ab47bc"}

    def dot_color(status: str, tier: int) -> str:
        return tier_pal[0] if status == "unemployed" else tier_pal.get(tier, "#aaa")

    def build_frame_data(day: int) -> list:
        snap = df_snap[df_snap["day"] == day].set_index("applicant_id")
        day_ev = df_ev[df_ev["day"] == day]
        hire_ev = day_ev[day_ev["event"] == "hired"]
        apply_ev = day_ev[day_ev["event"] == "applied"]
        fire_ev = day_ev[day_ev["event"].isin(["fired", "laid_off"])]

        # Applicant dots
        ax = [aid_to_pos[a][0] for a in applicant_ids]
        ay = [aid_to_pos[a][1] for a in applicant_ids]
        a_colors, a_hovers = [], []
        for aid in applicant_ids:
            if aid in snap.index:
                r = snap.loc[aid]
                status, tier = str(r["status"]), int(r.get("company_tier", 0))
                a_colors.append(dot_color(status, tier))
                a_hovers.append(
                    f"#{aid} | {status}<br>"
                    f"{r.get('company_name', '')}<br>"
                    f"Salary: ${float(r['salary']):,.0f} | Wealth: ${float(r['wealth']):,.0f}"
                )
            else:
                a_colors.append(tier_pal[0])
                a_hovers.append(f"#{aid}")

        # Company nodes, sized by employee count
        emp_cnt = snap[snap["status"] == "employed"]["company_id"].value_counts()
        cx = [cid_to_pos[c["company_id"]][0] for c in companies]
        cy = [cid_to_pos[c["company_id"]][1] for c in companies]
        c_sizes = [min(40, max(12, emp_cnt.get(c["company_id"], 0) * 2 + 10)) for c in companies]
        c_colors = [tier_pal.get(c["company_tier"], "#aaa") for c in companies]
        c_hovers = [
            f"<b>{c['company_name']}</b><br>Tier {c['company_tier']}<br>"
            f"Employees: {emp_cnt.get(c['company_id'], 0)}"
            for c in companies
        ]

        # Application lines (thin, dashed, faint)
        al_x: list = []
        al_y: list = []
        for _, row in apply_ev.iterrows():
            aid, cid = int(row["applicant_id"]), int(row["company_id"])
            if aid in aid_to_pos and cid in cid_to_pos:
                x0, y0 = aid_to_pos[aid]
                x1, y1 = cid_to_pos[cid]
                al_x.extend([x0, x1, None])
                al_y.extend([y0, y1, None])

        # Hire lines + midpoint labels
        hl_x: list = []
        hl_y: list = []
        lbl_x, lbl_y = [], []
        for _, row in hire_ev.iterrows():
            aid, cid = int(row["applicant_id"]), int(row["company_id"])
            if aid in aid_to_pos and cid in cid_to_pos:
                x0, y0 = aid_to_pos[aid]
                x1, y1 = cid_to_pos[cid]
                hl_x.extend([x0, x1, None])
                hl_y.extend([y0, y1, None])
                lbl_x.append((x0 + x1) / 2)
                lbl_y.append((y0 + y1) / 2 + 0.012)

        # Fire rings
        fire_aids = [
            int(r["applicant_id"]) for _, r in fire_ev.iterrows()
            if int(r["applicant_id"]) in aid_to_pos
        ]
        fr_x = [aid_to_pos[a][0] for a in fire_aids]
        fr_y = [aid_to_pos[a][1] for a in fire_aids]

        return [
            go.Scatter(  # 0: application lines
                x=al_x, y=al_y, mode="lines",
                line=dict(color="rgba(180,180,180,0.18)", width=0.8, dash="dot"),
                hoverinfo="skip", showlegend=False,
            ),
            go.Scatter(  # 1: hire lines
                x=hl_x, y=hl_y, mode="lines",
                line=dict(color="rgba(80,220,100,0.85)", width=2.5),
                hoverinfo="skip", showlegend=False,
            ),
            go.Scatter(  # 2: "Hired ✓" midpoint labels
                x=lbl_x, y=lbl_y, mode="text",
                text=["Hired ✓"] * len(lbl_x),
                textfont=dict(color="rgba(80,220,100,0.95)", size=8),
                hoverinfo="skip", showlegend=False,
            ),
            go.Scatter(  # 3: fire rings
                x=fr_x, y=fr_y, mode="markers",
                marker=dict(
                    color="rgba(0,0,0,0)", size=20,
                    line=dict(color="rgba(255,80,80,0.9)", width=2.5),
                ),
                hoverinfo="skip", showlegend=False,
            ),
            go.Scatter(  # 4: applicant dots
                x=ax, y=ay, mode="markers",
                marker=dict(color=a_colors, size=9,
                            line=dict(color="rgba(255,255,255,0.35)", width=0.5)),
                text=a_hovers, hoverinfo="text", showlegend=False,
            ),
            go.Scatter(  # 5: company squares
                x=cx, y=cy, mode="markers+text",
                marker=dict(color=c_colors, size=c_sizes, symbol="square",
                            line=dict(color="rgba(255,255,255,0.3)", width=1)),
                text=[c["company_name"] for c in companies],
                textposition="middle left",
                textfont=dict(size=7, color="rgba(255,255,255,0.6)"),
                hovertext=c_hovers, hoverinfo="text", showlegend=False,
            ),
        ]

    frames = []
    for day in days:
        cum_spend, cum_plat = cum_by_day.get(day, (0.0, 0.0))
        frames.append(
            go.Frame(
                data=build_frame_data(day),
                traces=list(range(6)),
                name=str(day),
                layout=go.Layout(
                    title_text=(
                        f"Day {day}  |  "
                        f"Applications: {len(df_ev[(df_ev['day']==day) & (df_ev['event']=='applied')])}  |  "
                        f"Hired: {len(df_ev[(df_ev['day']==day) & (df_ev['event']=='hired')])}  |  "
                        f"Fired/Laid off: {len(df_ev[(df_ev['day']==day) & (df_ev['event'].isin(['fired','laid_off']))])}"
                        f"  |  Applicant Spend: ${cum_spend:,.0f}"
                        f"  |  Platform Revenue: ${cum_plat:,.0f}"
                    )
                ),
            )
        )

    fig = go.Figure(data=build_frame_data(days[0]), frames=frames)

    fig.update_xaxes(range=[0, 1], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True)
    fig.update_yaxes(range=[0, 1], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True)

    tier_legend = [
        dict(x=0.005, y=1.0 - i * 0.055, xref="paper", yref="paper",
             text=f"● {lbl}", showarrow=False,
             font=dict(size=9, color=tier_pal[t]))
        for i, (t, lbl) in enumerate(
            [(0, "Unemployed"), (1, "Tier 1"), (2, "Tier 2"), (3, "Tier 3"), (4, "Tier 4"), (5, "Tier 5")]
        )
    ]

    fig.update_layout(
        title=f"Day {days[0]} | Job Market Interactions",
        height=750,
        plot_bgcolor="#12122a",
        paper_bgcolor="#0d0d1f",
        font=dict(color="white"),
        updatemenus=[{
            "type": "buttons",
            "y": -0.08, "x": 0.5, "xanchor": "center",
            "bgcolor": "#2a2a44",
            "buttons": [
                {"label": "▶ Play", "method": "animate",
                 "args": [None, {"frame": {"duration": 600, "redraw": True},
                                 "transition": {"duration": 300, "easing": "cubic-in-out"},
                                 "fromcurrent": True}]},
                {"label": "⏸ Pause", "method": "animate",
                 "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]},
            ],
        }],
        sliders=[{
            "steps": [
                {"method": "animate",
                 "args": [[str(d)], {"mode": "immediate",
                                     "transition": {"duration": 200, "easing": "cubic-in-out"},
                                     "frame": {"duration": 600, "redraw": True}}],
                 "label": str(d)}
                for d in days
            ],
            "x": 0.05, "len": 0.9,
            "bgcolor": "#2a2a44",
            "currentvalue": {"prefix": "Day: ", "visible": True, "font": {"color": "white"}},
            "pad": {"t": 50},
        }],
        annotations=[
            dict(x=0.22, y=1.04, xref="paper", yref="paper",
                 text="◉ Applicants", showarrow=False, font=dict(size=12)),
            dict(x=0.82, y=1.04, xref="paper", yref="paper",
                 text="■ Companies (size = employees)", showarrow=False, font=dict(size=12)),
            dict(x=0.54, y=1.04, xref="paper", yref="paper",
                 text="━ hired   ┄ applied   ○ fired",
                 showarrow=False, font=dict(size=10, color="rgba(160,230,160,0.85)")),
        ] + tier_legend,
    )

    target = os.path.join(output_dir, "animation_interactions.html")
    fig.write_html(target)
    print(f"Interaction animation → {target}")
    return target

def make_revenue_animation(daily_metrics_path: str, output_dir: str) -> str:
    dm = pd.read_csv(daily_metrics_path).sort_values("day").reset_index(drop=True)
    days = dm["day"].tolist()

    cum_spend    = (dm["company_boost_revenue_cumulative"] + dm["platform_boost_revenue_cumulative"]).tolist()
    cum_platform = dm["platform_boost_revenue_cumulative"].tolist()
    cum_company  = dm["company_boost_revenue_cumulative"].tolist()
    cum_quest    = dm["quest_currency_today"].cumsum().tolist()
    net_profit   = (dm["platform_boost_revenue_cumulative"] - dm["quest_currency_today"].cumsum()).tolist()
    daily_spend  = dm["boost_spend_today"].tolist()

    y_max = max(cum_spend) * 1.12
    daily_max = max(daily_spend) * 1.2

    def build_traces(i: int) -> list:
        xs = days[:i+1]
        return [
            go.Scatter(x=xs, y=cum_spend[:i+1], mode="lines",
                       line=dict(color="#ffa726", width=2.5), name="Total Applicant Spend", yaxis="y"),
            go.Scatter(x=xs, y=cum_platform[:i+1], mode="lines",
                       line=dict(color="#ab47bc", width=2.5), name="Platform Boost Revenue", yaxis="y"),
            go.Scatter(x=xs, y=cum_company[:i+1], mode="lines",
                       line=dict(color="#42a5f5", width=2.5), name="Company Revenue Share", yaxis="y"),
            go.Scatter(x=xs, y=cum_quest[:i+1], mode="lines",
                       line=dict(color="#e84040", width=1.5, dash="dash"), name="Quest Payouts (cumul.)", yaxis="y"),
            go.Scatter(x=xs, y=net_profit[:i+1], mode="lines",
                       line=dict(color="#66bb6a", width=2.5, dash="dot"), name="Net Platform Profit", yaxis="y"),
            go.Bar(x=xs, y=daily_spend[:i+1],
                   marker_color="rgba(255,167,38,0.45)", name="Daily Boost Spend", yaxis="y2"),
        ]

    frames = [
        go.Frame(
            data=build_traces(i),
            traces=list(range(6)),
            name=str(day),
            layout=go.Layout(title_text=(
                f"Day {day}  |  Total Applicant Spend: ${cum_spend[i]:,.0f}"
                f"  |  Platform Revenue: ${cum_platform[i]:,.0f}"
                f"  |  Net Profit: ${net_profit[i]:,.0f}"
            )),
        )
        for i, day in enumerate(days)
    ]

    fig = go.Figure(
        data=build_traces(0),
        frames=frames,
        layout=go.Layout(
            title=f"Day {days[0]} | Platform Revenue",
            height=680,
            plot_bgcolor="#12122a",
            paper_bgcolor="#0d0d1f",
            font=dict(color="white"),
            barmode="overlay",
            xaxis=dict(
                title="Day", range=[min(days)-1, max(days)+1],
                gridcolor="rgba(255,255,255,0.06)",
            ),
            yaxis=dict(
                title="Cumulative ($)", domain=[0.44, 1.0],
                range=[0, y_max],
                gridcolor="rgba(255,255,255,0.06)",
            ),
            yaxis2=dict(
                title="Daily Spend ($)", domain=[0.0, 0.38],
                range=[0, daily_max],
                gridcolor="rgba(255,255,255,0.06)",
                anchor="x",
            ),
            legend=dict(x=0.01, y=0.97, bgcolor="rgba(18,18,42,0.85)", font=dict(size=10)),
            annotations=[
                dict(x=0.01, y=1.01, xref="paper", yref="paper",
                     text="<b>Cumulative Revenue Streams</b>", showarrow=False,
                     font=dict(size=11, color="rgba(255,255,255,0.65)"), xanchor="left"),
                dict(x=0.01, y=0.39, xref="paper", yref="paper",
                     text="<b>Daily Boost Spend</b>", showarrow=False,
                     font=dict(size=11, color="rgba(255,255,255,0.65)"), xanchor="left"),
            ],
            updatemenus=[{
                "type": "buttons",
                "y": -0.1, "x": 0.5, "xanchor": "center",
                "bgcolor": "#2a2a44",
                "buttons": [
                    {"label": "▶ Play", "method": "animate",
                     "args": [None, {"frame": {"duration": 150, "redraw": True},
                                     "transition": {"duration": 80, "easing": "cubic-in-out"},
                                     "fromcurrent": True}]},
                    {"label": "⏸ Pause", "method": "animate",
                     "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]},
                ],
            }],
            sliders=[{
                "steps": [
                    {"method": "animate",
                     "args": [[str(d)], {"mode": "immediate",
                                         "transition": {"duration": 60, "easing": "cubic-in-out"},
                                         "frame": {"duration": 150, "redraw": True}}],
                     "label": str(d)}
                    for d in days
                ],
                "x": 0.05, "len": 0.9,
                "bgcolor": "#2a2a44",
                "currentvalue": {"prefix": "Day: ", "visible": True, "font": {"color": "white"}},
                "pad": {"t": 50},
            }],
        ),
    )

    target = os.path.join(output_dir, "animation_revenue.html")
    fig.write_html(target)
    print(f"Revenue animation → {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate animations from simulation output")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--applicant-id", type=int, default=0, help="Applicant ID for individual journey animation")
    args = parser.parse_args()

    snapshots = latest_file(args.output_dir, "applicant_snapshots_*.csv")
    daily = latest_file(args.output_dir, "daily_metrics_*.csv")
    events = latest_file(args.output_dir, "interaction_events_*.csv")
    
    make_population_animation(snapshots, daily, args.output_dir)
    make_population_animation_with_dots(snapshots, daily, args.output_dir)
    make_wealth_income_animation(snapshots, daily, args.output_dir)
    make_individual_animation(snapshots, args.output_dir, args.applicant_id)
    make_interaction_animation(snapshots, events, daily, args.output_dir)
    make_revenue_animation(daily, args.output_dir)