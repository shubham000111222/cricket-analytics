"""
Win Probability Model
Estimates the batting team's win probability ball-by-ball
using a logistic regression trained on IPL-style features.

Since we don't ship actual match data, we:
1. Generate synthetic IPL-like training data
2. Train a LogisticRegression model at startup
3. Use it to predict live win probability during simulation

For production: Replace with a model trained on real IPL datasets
(Kaggle: "IPL Complete Dataset" / "Cricket Win Prediction").
"""

import math
import pickle
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

# ── Optional sklearn ──────────────────────────────────────────────────────────
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    _sklearn_available = True
except ImportError:
    _sklearn_available = False


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def extract_features(
    total_runs: int,
    wickets: int,
    balls_bowled: int,       # 0-120 (20 overs)
    target: int,
    current_inning: int,
) -> np.ndarray:
    """
    Compute feature vector from match state.

    Features:
      1. run_rate_current         — runs per over so far
      2. required_run_rate        — runs per over needed (innings2) / NaN-proxy (innings1)
      3. wickets_in_hand          — 10 - wickets fallen
      4. balls_remaining          — 120 - balls_bowled
      5. runs_per_wicket          — total_runs / max(wickets,1)
      6. pressure_index           — rrr / crr (how much pressure is on batters)
      7. stage_of_innings         — balls_bowled / 120 (0→1)
      8. target_scaled            — target / 200 (normalised)
      9. deficit                  — runs needed / max(balls_remaining/6,1)
     10. wickets_utilisation      — wickets / 10
    """
    balls_remaining = max(0, 120 - balls_bowled)
    overs_bowled    = balls_bowled / 6
    overs_remaining = balls_remaining / 6

    crr = total_runs / max(overs_bowled, 0.1)
    rrr = max(0, (target - total_runs)) / max(overs_remaining, 0.1) if current_inning == 2 else 0

    wickets_in_hand  = 10 - wickets
    runs_per_wicket  = total_runs / max(wickets, 1)
    pressure         = rrr / max(crr, 0.1) if current_inning == 2 else 0
    stage            = balls_bowled / 120
    target_scaled    = target / 200 if target else 0
    deficit          = max(0, (target - total_runs)) / max(overs_remaining, 0.1) if current_inning == 2 else 0
    wkt_util         = wickets / 10

    return np.array([[
        crr, rrr, wickets_in_hand, balls_remaining,
        runs_per_wicket, pressure, stage, target_scaled, deficit, wkt_util,
    ]])


# ---------------------------------------------------------------------------
# Synthetic Training Data Generator
# ---------------------------------------------------------------------------
def _simulate_match() -> List[tuple]:
    """
    Simulate one full innings2 (chase) and label each game state
    as win (1) or loss (0) based on final outcome.
    Returns list of (features, label) tuples.
    """
    target = random.randint(130, 220)
    wickets = 0
    runs = 0
    samples = []

    outcomes = [0, 0, 0, 1, 1, 2, 2, 4, 4, 6, -1, -1]  # -1 = wicket

    for ball in range(120):
        if wickets >= 10 or runs >= target:
            break
        o = random.choice(outcomes)
        if o == -1:
            wickets += 1
            o = 0
        runs += o

        feat = extract_features(runs, wickets, ball + 1, target, 2)
        samples.append((feat, None, runs, wickets, ball + 1, target))

    won = 1 if runs >= target else 0
    labelled = [(s[0], won) for s in samples]
    return labelled


def generate_training_data(n_matches: int = 3000):
    X_list, y_list = [], []
    for _ in range(n_matches):
        for feat, label in _simulate_match():
            X_list.append(feat[0])
            y_list.append(label)
    return np.array(X_list), np.array(y_list)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
MODEL_CACHE = Path(__file__).parent / "_win_prob_model.pkl"


def train_model(n_matches: int = 3000) -> Any:
    if not _sklearn_available:
        raise ImportError("Install scikit-learn: pip install scikit-learn")

    print("[Win Probability] Generating training data ...")
    X, y = generate_training_data(n_matches)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=500, C=1.0, random_state=42)),
    ])
    pipeline.fit(X, y)
    print(f"[Win Probability] Model trained on {len(X)} samples.")

    with open(MODEL_CACHE, "wb") as f:
        pickle.dump(pipeline, f)

    return pipeline


def load_or_train_model():
    if MODEL_CACHE.exists():
        try:
            with open(MODEL_CACHE, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return train_model()


# ---------------------------------------------------------------------------
# Win Probability Estimator
# ---------------------------------------------------------------------------
class WinProbabilityEstimator:
    """
    Ball-by-ball win probability estimator.
    Falls back to a heuristic formula if sklearn is unavailable.
    """

    def __init__(self, use_ml: bool = True):
        self.use_ml = use_ml and _sklearn_available
        self._model = None
        if self.use_ml:
            self._model = load_or_train_model()

    def predict(
        self,
        total_runs: int,
        wickets: int,
        balls_bowled: int,
        target: int,
        current_inning: int,
    ) -> Dict[str, float]:
        """
        Returns {batting_win_prob, bowling_win_prob} as percentages 0-100.
        """
        if current_inning == 1:
            # In first innings, estimate based on projected score vs typical IPL scores
            overs_bowled = balls_bowled / 6
            projected = (total_runs / max(overs_bowled, 0.1)) * 20
            wicket_penalty = wickets * 5
            projected_adj = projected - wicket_penalty
            p_bat = min(max((projected_adj - 140) / 80 * 100, 20), 80)
            return {"batting": round(p_bat, 1), "bowling": round(100 - p_bat, 1)}

        if self.use_ml and self._model is not None:
            feat = extract_features(total_runs, wickets, balls_bowled, target, current_inning)
            prob = self._model.predict_proba(feat)[0]
            # class 1 = batting team wins
            classes = list(self._model.classes_)
            bat_prob = prob[classes.index(1)] if 1 in classes else 0.5
            bat_prob = float(np.clip(bat_prob, 0.02, 0.98))
            return {"batting": round(bat_prob * 100, 1), "bowling": round((1 - bat_prob) * 100, 1)}

        return self._heuristic(total_runs, wickets, balls_bowled, target)

    @staticmethod
    def _heuristic(runs: int, wkts: int, balls: int, target: int) -> Dict[str, float]:
        needed = target - runs
        balls_left = 120 - balls
        if balls_left <= 0:
            win = 1.0 if runs >= target else 0.0
            return {"batting": round(win * 100, 1), "bowling": round((1 - win) * 100, 1)}

        rrr = needed / (balls_left / 6)
        wkts_in_hand = 10 - wkts
        # Sigmoid on (required RR - 9) * wickets weight
        x = (rrr - 9) * 0.5 - (wkts_in_hand - 5) * 0.2
        prob_loss = 1 / (1 + math.exp(-x))
        prob_win = 1 - prob_loss
        return {"batting": round(prob_win * 100, 1), "bowling": round(prob_loss * 100, 1)}


# ---------------------------------------------------------------------------
# Historical Win Probability Timeline Builder
# ---------------------------------------------------------------------------
def build_win_prob_timeline(
    balls_data: List[Dict],
    target: int,
    current_inning: int,
    estimator: Optional[WinProbabilityEstimator] = None,
) -> List[Dict]:
    """
    Reconstruct win probability for each ball in the timeline.
    balls_data: list of ball dicts from SimulatedMatchEngine.balls
    """
    if estimator is None:
        estimator = WinProbabilityEstimator(use_ml=False)

    timeline = []
    for ball in balls_data:
        balls_bowled = ball["over"] * 6 + ball["ball"]
        probs = estimator.predict(
            total_runs=ball["total_runs"],
            wickets=ball["wickets"],
            balls_bowled=balls_bowled,
            target=target,
            current_inning=current_inning,
        )
        timeline.append({
            "over": ball["over"],
            "ball": ball["ball"],
            "overs_str": ball["overs_str"],
            "total_runs": ball["total_runs"],
            "wickets": ball["wickets"],
            "batting_win_prob": probs["batting"],
            "bowling_win_prob": probs["bowling"],
            "is_wicket": ball.get("is_wicket", False),
            "is_boundary": ball.get("runs_scored", 0) in (4, 6),
            "runs_scored": ball.get("runs_scored", 0),
        })
    return timeline
