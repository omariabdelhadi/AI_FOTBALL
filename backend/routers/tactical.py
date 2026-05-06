# backend/routers/tactical.py

from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import pandas as pd
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.analytics.tactical import (
    calculate_tactical_fit,
    build_optimal_lineup,
    FORMATIONS
)
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


def load_players():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    return pd.DataFrame(list(db["players"].find({}, {"_id": 0})))


@router.get("/formations")
def get_formations():
    """Retourne toutes les formations disponibles"""
    return {"formations": list(FORMATIONS.keys())}


@router.get("/analyze")
def analyze(team: str, formation: str):
    """
    Analyse tactique d'une équipe pour une formation donnée.

    Exemple : GET /api/tactical/analyze?team=PSG&formation=4-3-3
    """
    try:
        df      = load_players()
        df_team = df[(df["team"] == team) & (df["rating"] > 0)].copy()

        if df_team.empty:
            raise HTTPException(status_code=404,
                                detail=f"Équipe '{team}' introuvable")

        if formation not in FORMATIONS:
            raise HTTPException(status_code=400,
                                detail=f"Formation '{formation}' invalide")

        df_fit    = calculate_tactical_fit(df_team, formation)
        df_lineup = build_optimal_lineup(df_team, formation)

        # Meilleure formation
        scores = {}
        for f in FORMATIONS:
            df_f = calculate_tactical_fit(df_team, f)
            if df_f is not None:
                scores[f] = round(df_f["tactical_fit"].mean(), 4)

        best_formation = max(scores, key=scores.get)

        return {
            "team":            team,
            "formation":       formation,
            "best_formation":  best_formation,
            "formation_scores": scores,
            "tactical_fit": [
                {
                    "name":         row["player_name"],
                    "position":     row["position"],
                    "rating":       round(float(row["rating"]), 3),
                    "tactical_fit": round(float(row["tactical_fit"]), 4)
                }
                for _, row in df_fit.sort_values("tactical_fit",
                                                  ascending=False).iterrows()
            ],
            "optimal_lineup": [
                {
                    "name":     row["player_name"],
                    "position": row["position"],
                    "rating":   round(float(row["rating"]), 3)
                }
                for _, row in df_lineup.iterrows()
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))