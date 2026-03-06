"""
Real-Time Cricket Analytics Dashboard
======================================
Live/simulated IPL match stats with:
  • Ball-by-ball commentary feed
  • Win probability model updating every ball
  • Run rate (current vs required) charts
  • Batting worm
  • Batter/Bowler scorecards
  • Wagon wheel (simulated)
  • Over breakdown heatmap
  • Pressure gauge

Run:
    streamlit run streamlit_app.py
"""

import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.api_client import CricketDataProvider, IPL_TEAMS, PLAYER_NAMES
from src.win_probability import WinProbabilityEstimator, build_win_prob_timeline
from src.visualizations import (
    win_probability_chart,
    run_rate_chart,
    worm_chart,
    wagon_wheel_chart,
    batter_performance_chart,
    bowler_performance_chart,
    over_breakdown_chart,
    pressure_gauge,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏏 Cricket Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body, .stApp { background-color: #0d1117; color: #e6edf3; }
.metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
    margin: 4px;
}
.metric-label { font-size: 0.75rem; color: #8b949e; margin-bottom: 4px; }
.metric-value { font-size: 1.8rem; font-weight: 700; color: #e6edf3; }
.metric-sub   { font-size: 0.8rem; color: #8b949e; margin-top: 2px; }
.ball-W { background:#7f1d1d; border-radius:50%; padding:3px 7px; font-weight:700; color:#fca5a5; }
.ball-4 { background:#14532d; border-radius:50%; padding:3px 7px; font-weight:700; color:#86efac; }
.ball-6 { background:#713f12; border-radius:50%; padding:3px 7px; font-weight:700; color:#fde68a; }
.ball-0 { background:#1f2937; border-radius:50%; padding:3px 7px; color:#9ca3af; }
.ball-n { background:#1e3a5f; border-radius:50%; padding:3px 7px; color:#93c5fd; }
.commentary-row { border-left: 3px solid #30363d; padding: 6px 12px; margin: 4px 0; background:#161b22; border-radius: 0 6px 6px 0; }
.section-header { font-size:1.1rem; font-weight:600; color:#58a6ff; margin:12px 0 6px; border-bottom:1px solid #30363d; padding-bottom:4px; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "provider": None,
        "estimator": None,
        "match_started": False,
        "paused": False,
        "all_balls": [],            # full ball-by-ball history
        "win_prob_timeline": [],
        "innings1_summary": None,
        "current_inning": 1,
        "target": None,
        "meta": {},
        "scorecard": {},
        "speed": 0.8,               # seconds between ball deliveries
        "team1": IPL_TEAMS[0],
        "team2": IPL_TEAMS[1],
        "auto_play": True,
        "tick_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/cricket.png", width=72)
    st.title("🏏 Match Control")
    st.divider()

    st.subheader("🆚 Teams")
    t1 = st.selectbox("Batting First", IPL_TEAMS, index=IPL_TEAMS.index(st.session_state.team1))
    remaining = [t for t in IPL_TEAMS if t != t1]
    t2 = st.selectbox("Batting Second", remaining, index=0)
    st.session_state.team1 = t1
    st.session_state.team2 = t2

    st.divider()
    st.subheader("⚙️ Settings")
    speed = st.slider("Delivery Speed (sec/ball)", 0.1, 3.0, 0.8, step=0.1)
    st.session_state.speed = speed
    balls_per_tick = st.slider("Balls per Refresh", 1, 6, 1)
    use_ml = st.toggle("ML Win Probability", value=True)
    st.session_state.auto_play = st.toggle("Auto Play", value=True)

    st.divider()
    col_s, col_p, col_r = st.columns(3)
    with col_s:
        start_btn = st.button("▶ Start", type="primary", use_container_width=True)
    with col_p:
        pause_btn = st.button("⏸ Pause", use_container_width=True)
    with col_r:
        reset_btn = st.button("↺ Reset", use_container_width=True)

    if start_btn:
        provider = CricketDataProvider(use_simulation=True)
        provider.new_match(t1, t2)
        estimator = WinProbabilityEstimator(use_ml=use_ml)
        st.session_state.provider = provider
        st.session_state.estimator = estimator
        st.session_state.match_started = True
        st.session_state.paused = False
        st.session_state.all_balls = []
        st.session_state.win_prob_timeline = []
        st.session_state.innings1_summary = None
        st.session_state.current_inning = 1
        st.session_state.target = None
        st.session_state.meta = provider.get_match_meta()
        st.session_state.scorecard = {}
        st.session_state.tick_count = 0
        st.rerun()

    if pause_btn:
        st.session_state.paused = not st.session_state.paused

    if reset_btn:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    # CricAPI live feed
    st.subheader("🌐 Live API (Optional)")
    api_key = st.text_input("CricAPI Key", type="password", placeholder="Your API key")
    if api_key and st.button("Fetch Live Matches"):
        try:
            from src.api_client import CricAPIClient
            client = CricAPIClient(api_key=api_key)
            matches = client.get_current_matches()
            for m in matches[:5]:
                st.write(f"• {m.get('name', '?')} — {m.get('status', '')}")
        except Exception as e:
            st.error(f"API error: {e}")


# ── MAIN CONTENT ───────────────────────────────────────────────────────────────
st.title("🏏 Real-Time Cricket Analytics Dashboard")

if not st.session_state.match_started:
    st.markdown("---")
    st.markdown(
        "### Select teams in the sidebar and click **▶ Start** to begin the simulation.\n\n"
        "Features:\n"
        "- Ball-by-ball simulation with live commentary\n"
        "- ML-powered win probability (updates every ball)\n"
        "- Run rate analysis, batting worm, wagon wheel\n"
        "- Full scorecards for batters and bowlers\n"
        "- Works 100% offline — no API key needed"
    )

    # Team showcase
    st.divider()
    cols = st.columns(5)
    for i, team in enumerate(IPL_TEAMS[:5]):
        with cols[i]:
            st.markdown(f"**{team.split()[-1]}**")
            players = PLAYER_NAMES.get(team, [])[:3]
            for p in players:
                st.markdown(f"<small>• {p}</small>", unsafe_allow_html=True)
    cols2 = st.columns(5)
    for i, team in enumerate(IPL_TEAMS[5:]):
        with cols2[i]:
            st.markdown(f"**{team.split()[-1]}**")
            players = PLAYER_NAMES.get(team, [])[:3]
            for p in players:
                st.markdown(f"<small>• {p}</small>", unsafe_allow_html=True)
    st.stop()


# ── Active match ───────────────────────────────────────────────────────────────
provider: CricketDataProvider = st.session_state.provider
estimator: WinProbabilityEstimator = st.session_state.estimator
meta = st.session_state.meta


# Tick simulation if auto-play and not paused
if st.session_state.auto_play and not st.session_state.paused:
    tick_result = provider.tick(balls_per_tick=balls_per_tick)
    new_balls = tick_result["new_balls"]
    sc = tick_result["scorecard"]
    st.session_state.scorecard = sc
    st.session_state.current_inning = tick_result["inning"]

    # Detect innings transition
    if tick_result["innings1_summary"] and st.session_state.innings1_summary is None:
        st.session_state.innings1_summary = tick_result["innings1_summary"]
        st.session_state.target = st.session_state.innings1_summary["target"]

    target = st.session_state.target or 180

    for ball in new_balls:
        st.session_state.all_balls.append(ball)
        balls_bowled = ball["over"] * 6 + ball["ball"]
        probs = estimator.predict(
            total_runs=ball["total_runs"],
            wickets=ball["wickets"],
            balls_bowled=balls_bowled,
            target=target,
            current_inning=st.session_state.current_inning,
        )
        st.session_state.win_prob_timeline.append({
            **ball,
            "batting_win_prob": probs["batting"],
            "bowling_win_prob": probs["bowling"],
            "is_boundary": ball.get("runs_scored", 0) in (4, 6),
        })

    st.session_state.meta = tick_result["meta"]
    st.session_state.tick_count += 1


meta  = st.session_state.meta
sc    = st.session_state.scorecard
balls = st.session_state.all_balls
wpt   = st.session_state.win_prob_timeline
inning = st.session_state.current_inning
target = st.session_state.target
inning1 = st.session_state.innings1_summary

batting_team  = meta.get("innings1_team", t1) if inning == 1 else meta.get("innings2_team", t2)
bowling_team  = meta.get("innings2_team", t2) if inning == 1 else meta.get("innings1_team", t1)
current_balls = [b for b in balls if b["inning"] == inning]


# ── Match header ───────────────────────────────────────────────────────────────
col_title, col_status = st.columns([4, 1])
with col_title:
    st.markdown(
        f"### {meta.get('innings1_team','')} vs {meta.get('innings2_team','')}  "
        f"<small style='color:#8b949e'>• {meta.get('venue','')}</small>",
        unsafe_allow_html=True,
    )
    toss_txt = f"🪙 {meta.get('toss_winner','')} won the toss and chose to {meta.get('toss_decision','bat')}"
    st.markdown(f"<small>{toss_txt}</small>", unsafe_allow_html=True)
with col_status:
    status = "🔴 LIVE" if not sc.get("innings_complete") else "✅ Full"
    st.markdown(f"<div style='text-align:right;font-size:1.1rem;font-weight:700;color:#ff4b4b'>{status}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:right;color:#8b949e;font-size:0.8rem'>Innings {inning}</div>", unsafe_allow_html=True)

st.divider()


# ── Top scoreboard row ─────────────────────────────────────────────────────────
total_runs = sc.get("total_runs", 0)
wickets    = sc.get("wickets", 0)
overs      = sc.get("overs", "0.0")
run_rate   = sc.get("run_rate", 0.0)

if inning1:
    inn1_score = f"{inning1['score']}/{inning1['wickets']} ({inning1['overs']})"
else:
    inn1_score = "—"

req_rr = "—"
runs_needed = 0
if target and inning == 2:
    runs_needed = max(0, target - total_runs)
    try:
        ov_done = float(overs.split(".")[0]) + float(overs.split(".")[1]) / 6
        balls_left = max(0, 120 - int(ov_done * 6))
        req_rr = f"{runs_needed / max(balls_left / 6, 0.1):.2f}" if balls_left else "—"
    except Exception:
        req_rr = "—"

metrics = [
    ("Score", f"{total_runs}/{wickets}", overs + " ov"),
    ("Run Rate", str(run_rate), "current"),
    ("Required RR", req_rr, f"{runs_needed} to win" if inning == 2 else "—"),
    ("Innings 1", inn1_score, meta.get("innings1_team", "")),
    ("Target", str(target) if target else "—", "to win" if inning == 2 else ""),
]

cols = st.columns(len(metrics))
for col, (label, val, sub) in zip(cols, metrics):
    with col:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">{label}</div>'
            f'<div class="metric-value">{val}</div>'
            f'<div class="metric-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")


# ── Win Probability + Gauge ────────────────────────────────────────────────────
col_wp, col_gauge = st.columns([3, 1])

with col_wp:
    st.markdown('<div class="section-header">📈 Win Probability</div>', unsafe_allow_html=True)
    current_wpt = [w for w in wpt if w["inning"] == inning]
    fig_wp = win_probability_chart(current_wpt, batting_team, bowling_team, target)
    st.plotly_chart(fig_wp, use_container_width=True)

with col_gauge:
    st.markdown('<div class="section-header">🎯 Pressure Gauge</div>', unsafe_allow_html=True)
    latest_prob = current_wpt[-1]["batting_win_prob"] if current_wpt else 50.0
    fig_gauge = pressure_gauge(latest_prob, batting_team.split()[-1])
    st.plotly_chart(fig_gauge, use_container_width=True)


# ── Charts row 2 ───────────────────────────────────────────────────────────────
col_rr, col_worm = st.columns(2)

with col_rr:
    st.markdown('<div class="section-header">📉 Run Rate</div>', unsafe_allow_html=True)
    fig_rr = run_rate_chart(current_balls, target, inning)
    st.plotly_chart(fig_rr, use_container_width=True)

with col_worm:
    st.markdown('<div class="section-header">🐛 Batting Worm</div>', unsafe_allow_html=True)
    fig_worm = worm_chart(current_balls, batting_team)
    st.plotly_chart(fig_worm, use_container_width=True)


# ── Charts row 3 ───────────────────────────────────────────────────────────────
col_over, col_wagon = st.columns(2)

with col_over:
    st.markdown('<div class="section-header">📊 Over Breakdown</div>', unsafe_allow_html=True)
    fig_ob = over_breakdown_chart(current_balls)
    st.plotly_chart(fig_ob, use_container_width=True)

with col_wagon:
    st.markdown('<div class="section-header">🎯 Wagon Wheel</div>', unsafe_allow_html=True)
    fig_ww = wagon_wheel_chart(current_balls)
    st.plotly_chart(fig_ww, use_container_width=True)


# ── Scorecards ─────────────────────────────────────────────────────────────────
col_bat, col_bowl = st.columns(2)

engine = provider.engine if provider else None

with col_bat:
    st.markdown('<div class="section-header">🏏 Batter Scorecard</div>', unsafe_allow_html=True)
    if engine:
        fig_bat = batter_performance_chart(engine.batter_runs, engine.batter_balls)
        st.plotly_chart(fig_bat, use_container_width=True)

with col_bowl:
    st.markdown('<div class="section-header">🎳 Bowler Figures</div>', unsafe_allow_html=True)
    if engine:
        fig_bowl = bowler_performance_chart(engine.bowler_wickets, engine.bowler_runs_conceded)
        st.plotly_chart(fig_bowl, use_container_width=True)


# ── Live commentary feed ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">🎙️ Ball-by-Ball Commentary</div>', unsafe_allow_html=True)

def _format_ball(ball: dict) -> str:
    r = ball.get("runs_scored", 0)
    extra = ball.get("extra", 0)
    is_w = ball.get("is_wicket", False)
    striker = ball.get("striker", "?")
    bowler = ball.get("bowler", "?")
    overs_s = ball.get("overs_str", "?.?")
    wkt_type = ball.get("wicket_type", "")

    if is_w:
        ball_badge = f'<span class="ball-W">W</span>'
        desc = f"OUT! {striker} — {wkt_type}. Bowled by {bowler}."
    elif extra > 0:
        extra_type = "nb" if ball.get("outcome") == "nb" else "wd"
        ball_badge = f'<span class="ball-0">{extra_type}</span>'
        desc = f"Extra! Bowled by {bowler}."
    elif r == 4:
        ball_badge = f'<span class="ball-4">4</span>'
        desc = f"FOUR! {striker} sends it to the boundary off {bowler}."
    elif r == 6:
        ball_badge = f'<span class="ball-6">6</span>'
        desc = f"SIX! {striker} launches it over the fence off {bowler}!"
    elif r == 0:
        ball_badge = f'<span class="ball-0">•</span>'
        desc = f"Dot ball. {bowler} beats {striker}."
    else:
        ball_badge = f'<span class="ball-n">{r}</span>'
        desc = f"{striker} takes {r} run{'s' if r>1 else ''} off {bowler}."

    score = f"{ball['total_runs']}/{ball['wickets']}"
    return (
        f'<div class="commentary-row">'
        f'<span style="color:#8b949e;font-size:0.8rem">{overs_s} &nbsp;</span>'
        f'{ball_badge} &nbsp; {desc} &nbsp;'
        f'<span style="float:right;color:#8b949e">{score}</span>'
        f'</div>'
    )

# Show last 20 balls reversed
recent = list(reversed(current_balls[-20:]))
for ball in recent:
    st.markdown(_format_ball(ball), unsafe_allow_html=True)


# ── Auto-refresh ───────────────────────────────────────────────────────────────
if st.session_state.auto_play and not st.session_state.paused:
    engine = provider.engine if provider else None
    if engine and not engine.completed:
        time.sleep(st.session_state.speed)
        st.rerun()
    elif engine and engine.completed and inning == 1:
        time.sleep(1.5)
        st.rerun()
    else:
        # Match over
        if engine:
            st.divider()
            e = engine
            if e.total_runs >= (target or 0) and inning == 2:
                winner = meta.get("innings2_team", t2)
                margin = 10 - e.wickets
                st.success(f"🏆 {winner} WIN by {margin} wickets!")
            elif inning == 2:
                winner = meta.get("innings1_team", t1)
                margin = (target or 0) - e.total_runs - 1
                st.success(f"🏆 {winner} WIN by {margin} runs!")
            st.balloons()
