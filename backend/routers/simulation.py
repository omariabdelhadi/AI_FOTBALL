# backend/routers/simulation.py

from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.machine_learning.monte_carlo import simulate_match, simulate_with_opponent
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


@router.get("/teams")
def get_teams():
    """Retourne toutes les équipes disponibles"""
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    df     = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))
    teams  = sorted(df["team"].unique().tolist())
    return {"teams": teams}


@router.get("/predict")
def simulate(
    team:               str,
    opponent:           str,
    opponent_strength:  float = 0.5,
    home:               bool  = True,
    n_simulations:      int   = 10000
):
    """
    Simule un match entre deux équipes.

    Exemple : GET /api/simulation/predict?team=PSG&opponent=Lyon&home=true
    """
    try:
        client = MongoClient(MONGO_URI)
        db     = client["smartlineup"]

        df = pd.DataFrame(list(db["fixtures"].find({}, {"_id": 0})))

        keyword   = team.split()[0]
        mask_home = df["home_team"].str.contains(keyword, case=False, na=False)
        mask_away = df["away_team"].str.contains(keyword, case=False, na=False)

        df_home = df[mask_home].copy()
        df_away = df[mask_away].copy()
        df_all  = df[mask_home | mask_away].copy()

        total = len(df_all)

        if total == 0:
            df_all = df
            total  = len(df)
            wins   = len(df[df["result"] == "W"])
            draws  = len(df[df["result"] == "D"])
            loses  = total - wins - draws
        else:
            wins  = len(df_home[df_home["result"] == "W"]) + \
                    len(df_away[df_away["result"] == "L"])
            draws = len(df_all[df_all["result"] == "D"])
            loses = total - wins - draws

        base_probs = {
            "win":  wins  / total,
            "draw": draws / total,
            "loss": loses / total
        }

        adj     = simulate_with_opponent(base_probs, opponent_strength, home)
        results = simulate_match(adj["win"], adj["draw"], adj["loss"], n_simulations)

        return {
            "team":          team,
            "opponent":      opponent,
            "home":          home,
            "n_simulations": n_simulations,
            "prob_win":      f"{results['prob_win']:.2%}",
            "prob_draw":     f"{results['prob_draw']:.2%}",
            "prob_loss":     f"{results['prob_loss']:.2%}",
            "wins":          results["wins"],
            "draws":         results["draws"],
            "losses":        results["losses"],
            "favori":        team if results["prob_win"] >= results["prob_loss"] else opponent
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))