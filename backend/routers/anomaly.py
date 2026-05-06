# backend/routers/anomaly.py

from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import pandas as pd
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.machine_learning.anomaly import detect_anomalies
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


def load_players():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    return pd.DataFrame(list(db["players"].find({}, {"_id": 0})))


@router.get("/detect")
def detect(league: str = None, team: str = None):
    """
    Détecte les anomalies de performance.

    Exemple : GET /api/anomaly/detect?league=Ligue 1&team=PSG
    """
    try:
        df = load_players()
        df = df[df["rating"] > 0].copy()

        if league:
            df = df[df["league"] == league]
        if team:
            df = df[df["team"] == team]

        if df.empty:
            raise HTTPException(status_code=404, detail="Aucun joueur trouvé")

        df = detect_anomalies(df)

        return {
            "total":          len(df),
            "normal":         len(df[df["anomaly_type"] == "Normal"]),
            "surperformance": len(df[df["anomaly_type"] == "Surperformance"]),
            "sous_performance": len(df[df["anomaly_type"] == "Sous-performance"]),
            "attention":      len(df[df["anomaly_type"] == "Attention"]),
            "players": [
                {
                    "name":             row["player_name"],
                    "team":             row["team"],
                    "league":           row.get("league", ""),
                    "position":         row["position"],
                    "rating":           round(float(row["rating"]), 3),
                    "performance_score": round(float(row["performance_score"]), 4),
                    "anomaly_score":    round(float(row["anomaly_score"]), 4),
                    "anomaly_type":     row["anomaly_type"]
                }
                for _, row in df.sort_values("anomaly_score", ascending=False).iterrows()
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))