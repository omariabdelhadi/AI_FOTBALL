# backend/routers/pass_network.py

from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.analytics.pass_network import build_pass_network, calculate_centrality
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


@router.get("/analyze")
def analyze_pass_network(team: str):
    try:
        client     = MongoClient(MONGO_URI)
        db         = client["smartlineup"]
        df_players = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))

        # Filtrer les joueurs de l'équipe
        df_team = df_players[
            (df_players["team"] == team) &
            (df_players["rating"] > 0)
        ].copy()

        if df_team.empty:
            raise HTTPException(status_code=404,
                                detail=f"Équipe '{team}' introuvable")

        # Top 11 joueurs par minutes joués
        df_team = df_team.nlargest(11, "minutes").reset_index(drop=True)

        position_order = {
            "Goalkeeper": 0, "Defender": 1,
            "Midfielder": 2, "Forward": 3, "Attacker": 3
        }

        # Construire les noeuds
        nodes = []
        for _, row in df_team.iterrows():
            nodes.append({
                "player":     row["player_name"],
                "position":   row["position"],
                "passes":     int(row["passes_total"]),
                "key_passes": int(row["passes_key"]),
                "accuracy":   float(row["pass_accuracy"])
            })

        # Construire les arêtes
        edges = []
        players_list = df_team.to_dict(orient="records")

        for i in range(len(players_list)):
            for j in range(len(players_list)):
                if i == j:
                    continue
                p1   = players_list[i]
                p2   = players_list[j]
                r1   = position_order.get(p1["position"], 2)
                r2   = position_order.get(p2["position"], 2)
                if r2 >= r1:
                    w = round((float(p1["passes_total"]) + float(p2["passes_total"])) / 2, 2)
                    edges.append({"from": p1["player_name"], "to": p2["player_name"], "weight": w})

        # Calculer la centralité
        centrality = {n["player"]: 0 for n in nodes}
        for edge in edges:
            centrality[edge["from"]] += edge["weight"]
            centrality[edge["to"]]   += edge["weight"]

        max_val = max(centrality.values()) if centrality else 1
        centrality = {p: round(v / max_val, 4) for p, v in centrality.items()}

        # Joueur clé (exclure gardien)
        non_gk     = {p: s for p, s in centrality.items()
                      if any(n["player"] == p and n["position"] != "Goalkeeper" for n in nodes)}
        key_player = max(non_gk, key=non_gk.get) if non_gk else max(centrality, key=centrality.get)

        return {
            "team":       team,
            "key_player": key_player,
            "nodes":      nodes,
            "edges":      sorted(edges, key=lambda x: x["weight"], reverse=True)[:15],
            "centrality": [
                {"player": p, "score": s}
                for p, s in sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))