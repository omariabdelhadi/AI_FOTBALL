import os
import sys
import pickle
import pandas as pd  
from fastapi import APIRouter, HTTPException
from pymongo import MongoClient




sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from dotenv import load_dotenv
load_dotenv()

router=APIRouter()

MONGO_URI=os.getenv("MONGO_URI","mongodb://localhost:27017")

BASE_DIR = os.path.join(os.path.dirname(__file__), "../..")

def load_model():
    with open(os.path.join(BASE_DIR, "models/lineup_model.pkl"), "rb") as f:
        model = pickle.load(f)
    with open(os.path.join(BASE_DIR, "models/scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    return model, scaler

def load_players():
    client=MongoClient(MONGO_URI)
    db=client["smartlineup"]
    df=pd.DataFrame(list(db["players"].find({},{"_id":0})))
    return df

@router.get("/leagues")
def get_leagues():
    """Retourne toutes les ligues disponibles"""
    df=load_players()
    leagues=sorted(df["league"].unique().tolist())
    return {"leagues":leagues}

@router.get("/teams")
def get_teams(league:str):
    """Retourne toutes les équipes d'une ligue"""
    df=load_players()
    teams = sorted(df[df["league"] == league]["team"].unique().tolist())
    return {"teams":teams}

@router.get("/predict")
def predict_lineup(team: str):
    """
    Prédit les 11 titulaires d'une équipe.
    
    Exemple : GET /api/lineup/predict?team=Paris Saint-Germain
    """
    try:
        df     = load_players()
        model, scaler = load_model()

        df_team = df[df["team"] == team].copy()

        if df_team.empty:
            raise HTTPException(status_code=404,
                                detail=f"Équipe '{team}' introuvable")

        # Feature engineering
        feature_cols = [
            "performance_score", "fatigue_index", "defensive_impact",
            "anomaly_z", "rating", "pass_accuracy", "duels_won_pct",
            "goals", "assists", "minutes", "appearances",
            "match_importance", "recent_form",
            "is_goalkeeper", "is_defender", "is_midfielder", "is_forward"
        ]

        df_team["is_goalkeeper"] = (df_team["position"] == "Goalkeeper").astype(int)
        df_team["is_defender"]   = (df_team["position"] == "Defender").astype(int)
        df_team["is_midfielder"] = (df_team["position"] == "Midfielder").astype(int)
        df_team["is_forward"]    = (df_team["position"].isin(["Forward", "Attacker"])).astype(int)
        df_team["match_importance"] = 0.5
        df_team["recent_form"]      = 0.5

        for col in feature_cols:
            if col not in df_team.columns:
                df_team[col] = 0

        X        = df_team[feature_cols].fillna(0)
        X_scaled = scaler.transform(X)
        proba    = model.predict_proba(X_scaled)[:, 1]

        df_team["proba_starter"] = proba
        df_team = df_team.sort_values("proba_starter", ascending=False)

        titulaires  = df_team.head(11)
        remplacants = df_team.iloc[11:]

        return {
            "team": team,
            "titulaires": [
                {
                    "name":     row["player_name"],
                    "position": row["position"],
                    "rating":   round(float(row["rating"]), 3),
                    "proba":    f"{row['proba_starter']:.2%}"
                }
                for _, row in titulaires.iterrows()
            ],
            "remplacants": [
                {
                    "name":     row["player_name"],
                    "position": row["position"],
                    "rating":   round(float(row["rating"]), 3),
                    "proba":    f"{row['proba_starter']:.2%}"
                }
                for _, row in remplacants.head(7).iterrows()
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))








