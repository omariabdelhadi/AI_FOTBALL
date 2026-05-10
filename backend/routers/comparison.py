# backend/routers/comparison.py

from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import pandas as pd
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv()

router    = APIRouter()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


def load_players():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    return pd.DataFrame(list(db["players"].find({}, {"_id": 0})))


@router.get("/players")
def get_players(league: str = None, team: str = None):
    df = load_players()
    df = df[df["rating"] > 0]
    if league:
        df = df[df["league"] == league]
    if team:
        df = df[df["team"] == team]
    return {"players": sorted(df["player_name"].tolist())}


@router.get("/compare")
def compare_players(player1: str, player2: str):
    """
    Compare deux joueurs sur toutes leurs métriques.
    Exemple : GET /api/comparison/compare?player1=Mbappe&player2=Benzema
    """
    try:
        df = load_players()
        df = df[df["rating"] > 0].copy()

        p1 = df[df["player_name"] == player1]
        p2 = df[df["player_name"] == player2]

        if p1.empty:
            raise HTTPException(status_code=404,
                                detail=f"Joueur '{player1}' introuvable")
        if p2.empty:
            raise HTTPException(status_code=404,
                                detail=f"Joueur '{player2}' introuvable")

        p1 = p1.iloc[0]
        p2 = p2.iloc[0]

        # Métriques de comparaison
        metrics = [
            { "key": "rating",           "label": "Rating",           "max": 10  },
            { "key": "goals",            "label": "Buts",             "max": 30  },
            { "key": "assists",          "label": "Passes Décisives", "max": 20  },
            { "key": "pass_accuracy",    "label": "Précision Passes", "max": 100 },
            { "key": "duels_won_pct",    "label": "Duels Gagnés %",   "max": 1   },
            { "key": "defensive_impact", "label": "Impact Défensif",  "max": 50  },
            { "key": "performance_score","label": "Perf. Score",      "max": 1   },
            { "key": "fatigue_index",    "label": "Fatigue Index",    "max": 1   },
            { "key": "minutes",          "label": "Minutes",          "max": 3000},
            { "key": "shots_total",      "label": "Tirs",             "max": 100 },
        ]

        comparison = []
        p1_score   = 0
        p2_score   = 0

        for m in metrics:
            v1 = float(p1.get(m["key"], 0) or 0)
            v2 = float(p2.get(m["key"], 0) or 0)

            # Normaliser entre 0 et 100
            max_val = m["max"]
            v1_norm = round(min(v1 / max_val * 100, 100), 1)
            v2_norm = round(min(v2 / max_val * 100, 100), 1)

            winner = "player1" if v1 > v2 else "player2" if v2 > v1 else "draw"
            if winner == "player1": p1_score += 1
            if winner == "player2": p2_score += 1

            comparison.append({
                "metric":   m["label"],
                "player1":  round(v1, 3),
                "player2":  round(v2, 3),
                "p1_norm":  v1_norm,
                "p2_norm":  v2_norm,
                "winner":   winner
            })

        # Verdict global
        if p1_score > p2_score:
            verdict = player1
        elif p2_score > p1_score:
            verdict = player2
        else:
            verdict = "Égalité"

        return {
            "player1": {
                "name":     player1,
                "team":     p1["team"],
                "league":   p1["league"],
                "position": p1["position"],
                "age":      int(p1.get("age", 0) or 0),
            },
            "player2": {
                "name":     player2,
                "team":     p2["team"],
                "league":   p2["league"],
                "position": p2["position"],
                "age":      int(p2.get("age", 0) or 0),
            },
            "comparison": comparison,
            "score": {
                "player1": p1_score,
                "player2": p2_score
            },
            "verdict": verdict
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))