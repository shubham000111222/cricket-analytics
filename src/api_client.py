"""
CricAPI Client Module
Fetches live match data from CricAPI (https://cricapi.com) or
falls back to realistic simulated data for demo / offline use.

CricAPI Free tier: 100 requests/day — sufficient for demos.
Get your key at: https://cricapi.com/register
"""

import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import requests

# ── Constants ─────────────────────────────────────────────────────────────────
CRICAPI_BASE = "https://api.cricapi.com/v1"
DEFAULT_TIMEOUT = 10  # seconds

IPL_TEAMS = [
    "Mumbai Indians", "Chennai Super Kings", "Royal Challengers Bengaluru",
    "Kolkata Knight Riders", "Delhi Capitals", "Sunrisers Hyderabad",
    "Rajasthan Royals", "Punjab Kings", "Lucknow Super Giants", "Gujarat Titans",
]

VENUES = [
    "Wankhede Stadium, Mumbai",
    "M. A. Chidambaram Stadium, Chennai",
    "M. Chinnaswamy Stadium, Bengaluru",
    "Eden Gardens, Kolkata",
    "Arun Jaitley Stadium, Delhi",
    "Rajiv Gandhi Intl. Cricket Stadium, Hyderabad",
    "Sawai Mansingh Stadium, Jaipur",
    "Punjab Cricket Association Stadium, Mohali",
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Stadium, Lucknow",
    "Narendra Modi Stadium, Ahmedabad",
]

PLAYER_NAMES = {
    "Mumbai Indians":             ["Rohit Sharma", "Ishan Kishan", "Tilak Varma", "Suryakumar Yadav", "Tim David", "Hardik Pandya", "Jasprit Bumrah"],
    "Chennai Super Kings":        ["Ruturaj Gaikwad", "Devon Conway", "Ajinkya Rahane", "MS Dhoni", "Ravindra Jadeja", "Deepak Chahar", "Tushar Deshpande"],
    "Royal Challengers Bengaluru":["Virat Kohli","Faf du Plessis","Glenn Maxwell","Cameron Green","Dinesh Karthik","Mohammed Siraj","Yuzzvendra Chahal"],
    "Kolkata Knight Riders":      ["Shreyas Iyer","Phil Salt","Sunil Narine","Andre Russell","Venkatesh Iyer","Varun Chakaravarthy","Mitchell Starc"],
    "Delhi Capitals":             ["David Warner","Prithvi Shaw","Mitchell Marsh","Rishabh Pant","Axar Patel","Kuldeep Yadav","Anrich Nortje"],
    "Sunrisers Hyderabad":        ["Pat Cummins","Travis Head","Abhishek Sharma","Heinrich Klaasen","Aiden Markram","Bhuvneshwar Kumar","T Natarajan"],
    "Rajasthan Royals":           ["Sanju Samson","Jos Buttler","Yashasvi Jaiswal","Shimron Hetmyer","Riyan Parag","Trent Boult","Yuzvendra Chahal"],
    "Punjab Kings":               ["Shikhar Dhawan","Jonny Bairstow","Liam Livingstone","Sam Curran","Harpreet Brar","Arshdeep Singh","Kagiso Rabada"],
    "Lucknow Super Giants":       ["KL Rahul","Quinton de Kock","Marcus Stoinis","Nicholas Pooran","Deepak Hooda","Ravi Bishnoi","Mark Wood"],
    "Gujarat Titans":             ["Shubman Gill","Wriddhiman Saha","Hardik Pandya","David Miller","Rashid Khan","Mohammed Shami","Noor Ahmad"],
}


# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------
class CricAPIClient:
    """Wraps the CricAPI v1 REST endpoints."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CRICAPI_KEY", "")

    def _get(self, endpoint: str, params: dict = None) -> dict:
        if not self.api_key:
            raise ValueError("Set CRICAPI_KEY env variable or pass api_key to CricAPIClient.")
        params = params or {}
        params["apikey"] = self.api_key
        resp = requests.get(
            f"{CRICAPI_BASE}/{endpoint}",
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "failure":
            raise RuntimeError(f"CricAPI error: {data.get('reason', 'unknown')}")
        return data

    def get_current_matches(self) -> List[dict]:
        """List live / upcoming matches."""
        data = self._get("currentMatches")
        return data.get("data", [])

    def get_match_info(self, match_id: str) -> dict:
        data = self._get("match_info", {"id": match_id})
        return data.get("data", {})

    def get_match_scorecard(self, match_id: str) -> dict:
        data = self._get("match_scorecard", {"id": match_id})
        return data.get("data", {})


# ---------------------------------------------------------------------------
# Simulated Data Engine (offline / API-limit fallback)
# ---------------------------------------------------------------------------
class SimulatedMatchEngine:
    """
    Generates realistic ball-by-ball IPL match simulation.
    State is maintained across calls so the dashboard updates live.
    """

    OUTCOMES = [0, 0, 0, 1, 1, 1, 2, 2, 3, 4, 4, 6, "W", "W", "nb", "wd"]

    def __init__(self, team1: Optional[str] = None, team2: Optional[str] = None):
        self.team1 = team1 or random.choice(IPL_TEAMS)
        remaining   = [t for t in IPL_TEAMS if t != self.team1]
        self.team2  = team2 or random.choice(remaining)
        self.venue  = random.choice(VENUES)

        self.toss_winner = random.choice([self.team1, self.team2])
        self.toss_decision = random.choice(["bat", "field"])

        batting_first = (
            self.toss_winner if self.toss_decision == "bat"
            else (self.team2 if self.toss_winner == self.team1 else self.team1)
        )
        self.innings1_team = batting_first
        self.innings2_team = self.team2 if batting_first == self.team1 else self.team1

        self._reset_innings(1)

    # ── State ─────────────────────────────────────────────────────────────────
    def _reset_innings(self, inning: int):
        self.current_inning = inning
        self.balls: List[Dict] = []
        self.total_runs = 0
        self.wickets = 0
        self.extras = 0
        self.ball_number = 0         # legal balls faced
        self.over_number = 0
        self.ball_in_over = 0
        self.completed = False
        self._target: Optional[int] = None

        batting_team = self.innings1_team if inning == 1 else self.innings2_team
        self.batters = list(PLAYER_NAMES.get(batting_team, ["Batter " + str(i) for i in range(1, 8)]))
        self.current_batters = [self.batters[0], self.batters[1]]
        self.next_batter_idx = 2
        self.striker_idx = 0

        bowling_team = self.innings2_team if inning == 1 else self.innings1_team
        self.bowlers = list(PLAYER_NAMES.get(bowling_team, ["Bowler " + str(i) for i in range(1, 6)]))
        self.current_bowler = self.bowlers[0]
        self.batter_runs = {name: 0 for name in self.batters}
        self.batter_balls = {name: 0 for name in self.batters}
        self.bowler_wickets = {name: 0 for name in self.bowlers}
        self.bowler_runs_conceded = {name: 0 for name in self.bowlers}

    def set_target(self, target: int):
        self._target = target

    def deliver_ball(self) -> Optional[Dict]:
        """Simulate one ball. Returns ball_data dict or None if innings over."""
        if self.wickets >= 10 or self.over_number >= 20:
            self.completed = True
            return None

        outcome = random.choice(self.OUTCOMES)

        is_legal = outcome not in ("nb", "wd")
        runs_scored = 0
        extra = 0
        is_wicket = False
        wicket_type = None

        if outcome == "W":
            is_wicket = True
            wicket_type = random.choice(["Caught", "Bowled", "LBW", "Run out", "Stumped"])
            runs_scored = 0
        elif outcome == "nb":
            extra = 1
        elif outcome == "wd":
            extra = 1
        else:
            runs_scored = int(outcome)

        if is_legal:
            self.ball_number += 1
            self.ball_in_over += 1
            striker = self.current_batters[self.striker_idx]
            self.batter_runs[striker] += runs_scored
            self.batter_balls[striker] += 1

        self.total_runs += runs_scored + extra
        self.extras += extra
        self.bowler_runs_conceded[self.current_bowler] += runs_scored + extra

        if is_wicket:
            self.wickets += 1
            self.bowler_wickets[self.current_bowler] += 1
            if self.next_batter_idx < len(self.batters):
                self.current_batters[self.striker_idx] = self.batters[self.next_batter_idx]
                self.next_batter_idx += 1

        # Rotate strike on odd runs
        if runs_scored % 2 == 1:
            self.striker_idx = 1 - self.striker_idx

        # End of over
        if self.ball_in_over == 6:
            self.over_number += 1
            self.ball_in_over = 0
            self.striker_idx = 1 - self.striker_idx  # swap ends
            # Change bowler
            available = [b for b in self.bowlers if b != self.current_bowler]
            self.current_bowler = random.choice(available) if available else self.current_bowler

        if self.over_number >= 20 or self.wickets >= 10:
            self.completed = True

        # Early chase completion
        if self._target and self.total_runs >= self._target:
            self.completed = True

        overs_str = f"{self.over_number}.{self.ball_in_over}"

        ball_data = {
            "inning": self.current_inning,
            "over": self.over_number,
            "ball": self.ball_in_over,
            "overs_str": overs_str,
            "outcome": outcome,
            "runs_scored": runs_scored,
            "extra": extra,
            "is_wicket": is_wicket,
            "wicket_type": wicket_type,
            "total_runs": self.total_runs,
            "wickets": self.wickets,
            "striker": self.current_batters[self.striker_idx],
            "non_striker": self.current_batters[1 - self.striker_idx],
            "bowler": self.current_bowler,
            "timestamp": datetime.now().isoformat(),
        }
        self.balls.append(ball_data)
        return ball_data

    def deliver_batch(self, n: int = 6) -> List[Dict]:
        """Deliver n balls and return results."""
        results = []
        for _ in range(n):
            ball = self.deliver_ball()
            if ball is None:
                break
            results.append(ball)
        return results

    def get_scorecard(self) -> Dict:
        batting_team = self.innings1_team if self.current_inning == 1 else self.innings2_team
        return {
            "batting_team": batting_team,
            "total_runs": self.total_runs,
            "wickets": self.wickets,
            "overs": f"{self.over_number}.{self.ball_in_over}",
            "run_rate": round(self.total_runs / max(self.over_number + self.ball_in_over / 6, 0.1), 2),
            "extras": self.extras,
            "balls_timeline": self.balls,
        }

    def get_innings1_summary(self) -> Dict:
        """Call after innings 1 completes to get target."""
        return {
            "team": self.innings1_team,
            "score": self.total_runs,
            "wickets": self.wickets,
            "overs": f"{self.over_number}.{self.ball_in_over}",
            "target": self.total_runs + 1,
        }


# ---------------------------------------------------------------------------
# Unified Data Provider
# ---------------------------------------------------------------------------
class CricketDataProvider:
    """
    High-level class: uses real CricAPI when key is available, else simulation.
    """

    def __init__(self, use_simulation: bool = True):
        self.use_simulation = use_simulation
        self.engine: Optional[SimulatedMatchEngine] = None
        self._inning2_ready = False

        if not use_simulation:
            self.client = CricAPIClient()

    def new_match(self, team1: str = None, team2: str = None):
        self.engine = SimulatedMatchEngine(team1, team2)
        self._inning2_ready = False

    def get_match_meta(self) -> Dict:
        if self.engine is None:
            self.new_match()
        e = self.engine
        return {
            "team1": e.team1,
            "team2": e.team2,
            "venue": e.venue,
            "toss_winner": e.toss_winner,
            "toss_decision": e.toss_decision,
            "innings1_team": e.innings1_team,
            "innings2_team": e.innings2_team,
            "status": "Live" if not e.completed else "Innings 1 Complete",
        }

    def tick(self, balls_per_tick: int = 1) -> Dict:
        """Simulate `balls_per_tick` balls and return updated state."""
        if self.engine is None:
            self.new_match()

        e = self.engine
        new_balls = e.deliver_batch(balls_per_tick)

        if e.completed and e.current_inning == 1:
            summary1 = e.get_innings1_summary()
            e._reset_innings(2)
            e.set_target(summary1["target"])
            e.innings1_summary = summary1
            self._inning2_ready = True

        return {
            "new_balls": new_balls,
            "scorecard": e.get_scorecard(),
            "meta": self.get_match_meta(),
            "innings1_summary": getattr(e, "innings1_summary", None),
            "inning": e.current_inning,
            "innings_complete": e.completed,
        }
