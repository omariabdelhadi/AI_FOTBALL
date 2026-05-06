# backend/routers/transfer.py

from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import pandas as pd
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.analytics.transfer import (
    prepare_similarity_features,
    calculate_similarity,
    find_similar_players
)
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


def load_players():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    return pd.DataFrame(list(db["players"].find({}, {"_id": 0})))


@router.get("/similar")
def get_similar_players(player_name: str, top_n: int = 5):
    """
    Trouve les joueurs similaires à un joueur donné.

    Exemple : GET /api/transfer/similar?player_name=Mbappé
    """
    try:
        df = load_players()
        df_clean, X_scaled, _ = prepare_similarity_features(df)
        similarity_matrix     = calculate_similarity(X_scaled)

        similar = find_similar_players(df_clean, similarity_matrix,
                                       player_name, top_n)

        if similar is None:
            raise HTTPException(status_code=404,
                                detail=f"Joueur '{player_name}' introuvable")

        return {
            "player":  player_name,
            "similar": similar
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend")
def recommend(
    position:   str   = None,
    min_rating: float = 7.0,
    budget:     float = 50.0,
    league:     str   = None
):
    """
    Recommande des joueurs à recruter.

    Exemple : GET /api/transfer/recommend?position=Defender&min_rating=7.0
    """
    try:
        df = load_players()
        df = df[df["rating"] > 0].copy()

        # Facteur âge
        df["age_factor"] = df["age"].apply(
            lambda age: 1.5 if age < 23 else
                        1.2 if age < 26 else
                        1.0 if age < 30 else
                        0.7
        )

        # Facteur position
        df["pos_factor"] = df["position"].map({
            "Forward":    1.3,
            "Attacker":   1.3,
            "Midfielder": 1.1,
            "Defender":   1.0,
            "Goalkeeper": 0.9
        }).fillna(1.0)

        # Facteur performance
        df["perf_factor"] = (
            df["goals"] * 0.5 + df["assists"] * 0.3 + 1
        )

        # Valeur estimée
        df["estimated_value"] = (
            df["rating"] * df["minutes"] * 0.001 *
            df["age_factor"] * df["pos_factor"] * df["perf_factor"]
        ).round(2)

        if position:
            df = df[df["position"] == position]
        if league:
            df = df[df["league"] == league]

        df = df[
            (df["rating"] >= min_rating) &
            (df["estimated_value"] <= budget)
        ].sort_values("rating", ascending=False)

        if df.empty:
            return {"players": [], "message": "Aucun joueur trouvé"}

        return {
            "players": [
                {
                    "name":            row["player_name"],
                    "team":            row["team"],
                    "league":          row.get("league", ""),
                    "position":        row["position"],
                    "rating":          round(float(row["rating"]), 3),
                    "age":             int(row["age"]),
                    "estimated_value": round(float(row["estimated_value"]), 2)
                }
                for _, row in df.head(10).iterrows()
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))