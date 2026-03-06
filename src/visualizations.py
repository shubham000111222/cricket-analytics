"""
Visualizations Module
All Plotly charts for the cricket analytics dashboard.
"""

from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Brand colors ─────────────────────────────────────────────────────────────
TEAM1_COLOR  = "#1e88e5"    # Blue
TEAM2_COLOR  = "#e53935"    # Red
ACCENT       = "#ffd600"    # Yellow
BG           = "#0d1117"    # GitHub dark
CARD_BG      = "#161b22"
GRID_COLOR   = "#30363d"
TEXT_COLOR   = "#e6edf3"
GREEN        = "#2ea043"
ORANGE       = "#fb8500"


def _base_layout(**kwargs) -> dict:
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif"),
        xaxis=dict(gridcolor=GRID_COLOR, showgrid=True),
        yaxis=dict(gridcolor=GRID_COLOR, showgrid=True),
        margin=dict(l=40, r=20, t=50, b=40),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. Win Probability Chart (headline chart)
# ---------------------------------------------------------------------------
def win_probability_chart(
    timeline: List[Dict],
    team_bat: str,
    team_bowl: str,
    target: Optional[int] = None,
) -> go.Figure:
    if not timeline:
        fig = go.Figure()
        fig.update_layout(title="Win Probability — No data yet", **_base_layout())
        return fig

    df = pd.DataFrame(timeline)
    overs = df["overs_str"].tolist()

    fig = go.Figure()

    # Batting team fill band
    fig.add_trace(go.Scatter(
        x=overs, y=df["batting_win_prob"],
        fill="tozeroy",
        fillcolor=f"rgba(30,136,229,0.20)",
        line=dict(color=TEAM1_COLOR, width=2.5),
        name=f"{team_bat} Win%",
        hovertemplate="Over %{x}<br>Win Prob: %{y:.1f}%<extra></extra>",
    ))

    # Bowling team overlay
    fig.add_trace(go.Scatter(
        x=overs, y=df["bowling_win_prob"],
        line=dict(color=TEAM2_COLOR, width=2.5, dash="dot"),
        name=f"{team_bowl} Win%",
        hovertemplate="Over %{x}<br>Win Prob: %{y:.1f}%<extra></extra>",
    ))

    # Mark wickets
    wickets_df = df[df["is_wicket"] == True]
    if not wickets_df.empty:
        fig.add_trace(go.Scatter(
            x=wickets_df["overs_str"],
            y=wickets_df["batting_win_prob"],
            mode="markers",
            marker=dict(symbol="x", size=12, color=ACCENT, line=dict(width=2)),
            name="Wicket",
            hovertemplate="Wicket at %{x}<br>Win Prob: %{y:.1f}%<extra></extra>",
        ))

    # Mark boundaries
    boundary_df = df[df["is_boundary"] == True]
    if not boundary_df.empty:
        fig.add_trace(go.Scatter(
            x=boundary_df["overs_str"],
            y=boundary_df["batting_win_prob"],
            mode="markers",
            marker=dict(symbol="diamond", size=9, color=GREEN),
            name="Boundary",
            hovertemplate="Boundary at %{x}<br>Win Prob: %{y:.1f}%<extra></extra>",
        ))

    fig.add_hline(y=50, line_dash="dash", line_color=GRID_COLOR, opacity=0.6)

    title = f"Win Probability — {team_bat} vs {team_bowl}"
    if target:
        title += f" | Target: {target}"

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Over",
        yaxis_title="Win Probability (%)",
        yaxis=dict(range=[0, 100], gridcolor=GRID_COLOR),
        legend=dict(orientation="h", y=-0.15),
        height=400,
        **_base_layout(),
    )
    return fig


# ---------------------------------------------------------------------------
# 2. Run Rate Comparison Chart
# ---------------------------------------------------------------------------
def run_rate_chart(
    balls_data: List[Dict],
    target: Optional[int] = None,
    innings: int = 2,
) -> go.Figure:
    if not balls_data:
        fig = go.Figure()
        fig.update_layout(title="Run Rate — No data", **_base_layout())
        return fig

    overs, crr_list, rrr_list = [], [], []
    for ball in balls_data:
        over = ball["over"] + ball["ball"] / 6
        overs.append(round(over, 2))
        crr = ball["total_runs"] / max(over, 0.1)
        crr_list.append(round(crr, 2))

        if innings == 2 and target:
            balls_done = ball["over"] * 6 + ball["ball"]
            balls_left = 120 - balls_done
            runs_needed = target - ball["total_runs"]
            rrr = runs_needed / max(balls_left / 6, 0.1) if balls_left > 0 else 0
            rrr_list.append(round(max(0, rrr), 2))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=overs, y=crr_list,
        mode="lines",
        line=dict(color=TEAM1_COLOR, width=2.5),
        name="Current RR",
        fill="tozeroy",
        fillcolor="rgba(30,136,229,0.12)",
    ))

    if rrr_list:
        fig.add_trace(go.Scatter(
            x=overs, y=rrr_list,
            mode="lines",
            line=dict(color=TEAM2_COLOR, width=2.5, dash="dash"),
            name="Required RR",
        ))

    fig.update_layout(
        title="Run Rate Comparison",
        xaxis_title="Overs",
        yaxis_title="Runs per Over",
        legend=dict(orientation="h", y=-0.15),
        height=320,
        **_base_layout(),
    )
    return fig


# ---------------------------------------------------------------------------
# 3. Over-by-over Worm Chart
# ---------------------------------------------------------------------------
def worm_chart(balls_data: List[Dict], team_name: str) -> go.Figure:
    """Cumulative runs over time (classic cricket worm)."""
    overs, runs = [0], [0]
    for ball in balls_data:
        overs.append(round(ball["over"] + ball["ball"] / 6, 2))
        runs.append(ball["total_runs"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=overs, y=runs,
        mode="lines+markers",
        line=dict(color=ACCENT, width=2.5),
        marker=dict(size=3),
        name=team_name,
        fill="tozeroy",
        fillcolor="rgba(255,214,0,0.10)",
        hovertemplate="Over %{x:.1f}<br>Runs: %{y}<extra></extra>",
    ))

    fig.update_layout(
        title=f"Batting Worm — {team_name}",
        xaxis_title="Overs",
        yaxis_title="Cumulative Runs",
        height=300,
        **_base_layout(),
    )
    return fig


# ---------------------------------------------------------------------------
# 4. Wagon Wheel (directional shot distribution) — approximated
# ---------------------------------------------------------------------------
def wagon_wheel_chart(balls_data: List[Dict]) -> go.Figure:
    """Approximate wagon wheel using polar scatter plot."""
    angles, radii, colors, texts = [], [], [], []

    color_map = {0: GRID_COLOR, 1: TEXT_COLOR, 2: TEXT_COLOR, 4: GREEN, 6: ACCENT}

    for ball in balls_data:
        r = ball.get("runs_scored", 0)
        angle = np.random.uniform(0, 360)  # without real tracking we randomise
        radius = {0: 0.1, 1: 0.4, 2: 0.6, 4: 0.85, 6: 1.0}.get(r, 0.3)
        angles.append(angle)
        radii.append(radius)
        colors.append(color_map.get(r, TEXT_COLOR))
        texts.append(str(r))

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=radii, theta=angles,
        mode="markers",
        marker=dict(
            color=colors, size=8, opacity=0.8,
            line=dict(color=BG, width=0.5),
        ),
        text=texts,
        hovertemplate="Runs: %{text}<extra></extra>",
        name="Shots",
    ))

    fig.update_layout(
        title="Wagon Wheel (Simulated)",
        polar=dict(
            radialaxis=dict(visible=False),
            angularaxis=dict(
                tickmode="array",
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                ticktext=["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
                direction="clockwise",
                gridcolor=GRID_COLOR,
            ),
            bgcolor=CARD_BG,
        ),
        paper_bgcolor=BG,
        font=dict(color=TEXT_COLOR),
        height=350,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# 5. Batsman vs Bowler Heatmap
# ---------------------------------------------------------------------------
def batter_performance_chart(
    batter_runs: Dict[str, int],
    batter_balls: Dict[str, int],
    top_n: int = 8,
) -> go.Figure:
    data = [
        {
            "Batter": name,
            "Runs": runs,
            "Balls": batter_balls.get(name, 1),
            "SR": round(runs / max(batter_balls.get(name, 1), 1) * 100, 1),
        }
        for name, runs in batter_runs.items()
        if runs > 0 or batter_balls.get(name, 0) > 0
    ]
    df = pd.DataFrame(data).sort_values("Runs", ascending=True).tail(top_n)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Runs"], y=df["Batter"],
        orientation="h",
        marker=dict(
            color=df["SR"],
            colorscale="RdYlGn",
            colorbar=dict(title="Strike Rate", tickfont=dict(color=TEXT_COLOR)),
            line=dict(color=BG, width=0.5),
        ),
        text=[f"{r} ({b})" for r, b in zip(df["Runs"], df["Balls"])],
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Runs: %{x}<extra></extra>",
        name="Batters",
    ))

    fig.update_layout(
        title="Batter Scorecard",
        xaxis_title="Runs",
        height=max(250, len(df) * 40 + 80),
        **_base_layout(),
    )
    return fig


def bowler_performance_chart(
    bowler_wickets: Dict[str, int],
    bowler_runs: Dict[str, int],
    top_n: int = 6,
) -> go.Figure:
    data = [
        {
            "Bowler": name,
            "Wickets": bowler_wickets.get(name, 0),
            "Runs": runs,
        }
        for name, runs in bowler_runs.items()
    ]
    df = pd.DataFrame(data).sort_values("Wickets", ascending=False).head(top_n)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Bowler"], y=df["Wickets"],
        marker=dict(color=TEAM2_COLOR, opacity=0.85),
        name="Wickets",
        text=df["Wickets"], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=df["Bowler"], y=df["Runs"],
        marker=dict(color=ORANGE, opacity=0.65),
        name="Runs Conceded",
        yaxis="y2",
    ))

    fig.update_layout(
        title="Bowler Figures",
        barmode="overlay",
        yaxis=dict(title="Wickets", gridcolor=GRID_COLOR),
        yaxis2=dict(title="Runs", overlaying="y", side="right", gridcolor=GRID_COLOR),
        legend=dict(orientation="h", y=-0.15),
        height=320,
        **_base_layout(),
    )
    return fig


# ---------------------------------------------------------------------------
# 6. Over-by-over dot / boundary / wicket breakdown
# ---------------------------------------------------------------------------
def over_breakdown_chart(balls_data: List[Dict]) -> go.Figure:
    """Stacked bar showing dots, singles, doubles, fours, sixes, wickets per over."""
    if not balls_data:
        fig = go.Figure()
        fig.update_layout(title="Over Breakdown — No data", **_base_layout())
        return fig

    over_stats: Dict[int, Dict] = {}
    for ball in balls_data:
        ov = ball["over"]
        if ov not in over_stats:
            over_stats[ov] = {"dots": 0, "singles": 0, "doubles": 0, "fours": 0, "sixes": 0, "wickets": 0}
        r = ball.get("runs_scored", 0)
        if ball.get("is_wicket"):
            over_stats[ov]["wickets"] += 1
        elif r == 0:
            over_stats[ov]["dots"] += 1
        elif r == 1:
            over_stats[ov]["singles"] += 1
        elif r == 2:
            over_stats[ov]["doubles"] += 1
        elif r == 4:
            over_stats[ov]["fours"] += 1
        elif r == 6:
            over_stats[ov]["sixes"] += 1

    if not over_stats:
        fig = go.Figure()
        fig.update_layout(title="Over Breakdown — No data", **_base_layout())
        return fig

    overs  = sorted(over_stats.keys())
    labels = [f"Ov {o+1}" for o in overs]
    cats   = ["dots", "singles", "doubles", "fours", "sixes", "wickets"]
    cmap   = {"dots": GRID_COLOR, "singles": TEXT_COLOR, "doubles": ORANGE,
               "fours": GREEN, "sixes": ACCENT, "wickets": TEAM2_COLOR}

    fig = go.Figure()
    for cat in cats:
        fig.add_trace(go.Bar(
            x=labels,
            y=[over_stats[o].get(cat, 0) for o in overs],
            name=cat.title(),
            marker_color=cmap[cat],
        ))

    fig.update_layout(
        title="Over-by-Over Breakdown",
        barmode="stack",
        xaxis_title="Over",
        yaxis_title="Count",
        legend=dict(orientation="h", y=-0.18),
        height=310,
        **_base_layout(),
    )
    return fig


# ---------------------------------------------------------------------------
# 7. Pressure Gauge (win prob as gauge)
# ---------------------------------------------------------------------------
def pressure_gauge(
    batting_win_prob: float,
    batting_team: str,
) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=batting_win_prob,
        number=dict(suffix="%", font=dict(size=36, color=TEXT_COLOR)),
        delta=dict(reference=50, relative=False),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=TEXT_COLOR),
            bar=dict(color=TEAM1_COLOR),
            bgcolor=CARD_BG,
            bordercolor=GRID_COLOR,
            steps=[
                dict(range=[0, 30], color="#3d0000"),
                dict(range=[30, 50], color="#5a3000"),
                dict(range=[50, 70], color="#003a00"),
                dict(range=[70, 100], color="#002050"),
            ],
            threshold=dict(
                line=dict(color=ACCENT, width=3),
                thickness=0.75,
                value=50,
            ),
        ),
        title=dict(text=f"{batting_team} Win Prob", font=dict(color=TEXT_COLOR, size=14)),
    ))
    fig.update_layout(
        paper_bgcolor=BG,
        font=dict(color=TEXT_COLOR),
        height=260,
        margin=dict(l=30, r=30, t=50, b=20),
    )
    return fig
