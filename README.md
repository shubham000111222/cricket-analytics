---
title: Cricket Analytics Dashboard
emoji: 🏏
colorFrom: green
colorTo: blue
sdk: docker
pinned: true
---

# 🏏 Real-Time Cricket Analytics Dashboard

A live IPL/cricket match analytics dashboard with ball-by-ball simulation, win probability model, and rich interactive visualizations — all running in Streamlit.

---

## 🚀 Features

| Feature | Details |
|---|---|
| **Ball-by-ball simulation** | Realistic IPL match engine with full scorer |
| **ML Win Probability** | Logistic regression trained on synthetic IPL data, updates every ball |
| **Run Rate Analysis** | Current RR vs Required RR chart |
| **Batting Worm** | Cumulative runs chart |
| **Wagon Wheel** | Shot directional distribution (polar plot) |
| **Over Breakdown** | Dots/1s/2s/4s/6s/Wickets stacked bar |
| **Batter Scorecard** | Runs, balls, strike rate with colour-coded bars |
| **Bowler Figures** | Wickets + runs conceded dual-axis chart |
| **Pressure Gauge** | Win probability as a gauge |
| **Live Commentary** | Ball-by-ball text feed with colour-coded outcomes |
| **Live CricAPI** | Plug in your CricAPI key to fetch real IPL data |

---

## 📸 Dashboard Sections

```
Header: Match title, venue, toss info
↓
Scoreboard: Score | RR | Req RR | Target | Innings 1 summary
↓
Win Probability Chart + Pressure Gauge (updates every ball)
↓
Run Rate Chart    |    Batting Worm
↓
Over Breakdown    |    Wagon Wheel
↓
Batter Scorecard  |    Bowler Figures
↓
Live Commentary Feed (last 20 balls)
```

---

## ⚡ Quick Start

### Option 1 — Local Python

```bash
cd cricket-analytics

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

streamlit run streamlit_app.py
```

### Option 2 — Docker

```bash
docker-compose up --build
# Open http://localhost:8501
```

---

## 🌐 Using Live CricAPI Data

1. Register at [cricapi.com](https://cricapi.com/register) (free tier: 100 req/day)
2. Copy your API key
3. Enter it in the sidebar under **Live API** and click **Fetch Live Matches**

Or set it as an environment variable:
```bash
export CRICAPI_KEY=your_key_here
```

---

## 🤖 Win Probability Model

The model is a **Logistic Regression** trained on 3,000 synthetically simulated IPL innings.

**Features used:**
| Feature | Description |
|---|---|
| `run_rate_current` | Runs scored ÷ overs bowled |
| `required_run_rate` | Runs needed ÷ overs remaining |
| `wickets_in_hand` | 10 − wickets fallen |
| `balls_remaining` | 120 − balls bowled |
| `runs_per_wicket` | Total runs ÷ wickets (batting quality proxy) |
| `pressure_index` | RRR ÷ CRR |
| `stage_of_innings` | Balls bowled ÷ 120 |
| `target_scaled` | Target ÷ 200 |
| `deficit` | Runs needed ÷ overs remaining |
| `wickets_utilisation` | Wickets ÷ 10 |

> **Upgrade path:** Replace with a model trained on the Kaggle IPL Complete Dataset for real-world accuracy.

---

## 📁 Project Structure

```
cricket-analytics/
├── streamlit_app.py          # Main dashboard application
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── src/
    ├── __init__.py
    ├── api_client.py         # CricAPI client + ball-by-ball simulation engine
    ├── win_probability.py    # Feature engineering + LogisticRegression model
    └── visualizations.py     # All Plotly charts
```

---

## 🎯 Why This Project Stands Out

1. **Indian audience hook** — IPL + cricket = guaranteed recruiter interest
2. **Real-time stream simulation** — demonstrates event-driven data pipeline thinking
3. **ML in production context** — model updates live, shows deployment mindset
4. **Modular** — swap simulation for real CricAPI feed with zero code changes
5. **Rich visualizations** — 7+ chart types in a single dashboard

---

## 🔮 Future Enhancements

- WebSocket backend for true real-time CricAPI streaming
- Player career stats comparison view
- Head-to-head team analysis
- DRS / super-over simulation
- Fantasy cricket point predictor
- Mobile-responsive layout
