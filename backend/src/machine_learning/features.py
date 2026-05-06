# src/machine_learning/features.py

import pandas as pd
import numpy as np
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# ─────────────────────────────────────────
# 1. CHARGER LES DONNÉES DEPUIS MONGODB
# ─────────────────────────────────────────

def load_data():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]

    df_players     = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))
    df_lineups     = pd.DataFrame(list(db["lineups"].find({}, {"_id": 0})))
    df_fixtures    = pd.DataFrame(list(db["fixtures"].find({}, {"_id": 0})))
    df_match_stats = pd.DataFrame(list(db["match_stats"].find({}, {"_id": 0})))

    # Charger aussi les stats API originales
    api_players_path = "data/raw/players_team85_season2023.json"
    if os.path.exists(api_players_path):
        import json
        with open(api_players_path, "r", encoding="utf-8") as f:
            api_data = json.load(f)

        api_players = []
        for entry in api_data:
            player = entry["player"]
            for stats in entry["statistics"]:
                api_players.append({
                    "player_name":   player["name"],
                    "rating":        float(stats["games"]["rating"] or 0),
                    "goals":         stats["goals"]["total"] or 0,
                    "assists":       stats["goals"]["assists"] or 0,
                    "minutes":       stats["games"]["minutes"] or 0,
                    "appearances":   stats["games"]["appearences"] or 0,
                    "pass_accuracy": float(stats["passes"]["accuracy"] or 0),
                    "passes_total":  stats["passes"]["total"] or 0,
                    "passes_key":    stats["passes"]["key"] or 0,
                    "duels_total":   stats["duels"]["total"] or 0,
                    "duels_won":     stats["duels"]["won"] or 0,
                    "tackles":       stats["tackles"]["total"] or 0,
                    "interceptions": stats["tackles"]["interceptions"] or 0,
                    "blocks":        stats["tackles"]["blocks"] or 0,
                })

        df_api = pd.DataFrame(api_players)

        # Calculer les indices
        import numpy as np
        df_api["duels_won_pct"] = np.where(
            df_api["duels_total"] > 0,
            df_api["duels_won"] / df_api["duels_total"], 0
        )
        df_api["xg_proxy"] = np.where(
            df_api["appearances"] > 0,
            df_api["goals"] / df_api["appearances"], 0
        )
        df_api["performance_score"] = (
            0.3 * df_api["xg_proxy"] +
            0.2 * (df_api["pass_accuracy"] / 100) +
            0.2 * df_api["duels_won_pct"] +
            0.3 * (df_api["rating"] / 10)
        ).round(4)
        df_api["fatigue_index"] = np.where(
            df_api["appearances"] > 0,
            (df_api["minutes"] / df_api["appearances"]) / 90, 0
        ).round(4)
        df_api["defensive_impact"] = (
            0.4 * df_api["tackles"] +
            0.3 * df_api["interceptions"] +
            0.3 * df_api["blocks"]
        ).round(4)
        mean_ps = df_api["performance_score"].mean()
        std_ps  = df_api["performance_score"].std()
        df_api["anomaly_z"] = np.where(
            std_ps > 0,
            (df_api["performance_score"] - mean_ps) / std_ps, 0
        ).round(4)

        # Remplacer df_players par les stats API pour le ML
        df_players = df_api

    print(f"[CHARGÉ] players={len(df_players)}, lineups={len(df_lineups)}, fixtures={len(df_fixtures)}")
    return df_players, df_lineups, df_fixtures, df_match_stats


# ─────────────────────────────────────────
# 2. FEATURE : IMPORTANCE DU MATCH
# ─────────────────────────────────────────

def add_match_importance(df_fixtures):
    """
    Calcule l'importance d'un match selon la position dans la saison.
    Les derniers matchs sont plus importants (fin de saison).
    Valeur entre 0 et 1.
    """
    df = df_fixtures.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    total = len(df)
    df["match_importance"] = [(i + 1) / total for i in range(total)]

    return df


# ─────────────────────────────────────────
# 3. FEATURE : FORME RÉCENTE (5 DERNIERS MATCHS)
# ─────────────────────────────────────────

def add_recent_form(df_fixtures, team="Paris Saint-Germain"):
    """
    Calcule la forme récente de l'équipe sur les 5 derniers matchs.
    W=3pts, D=1pt, L=0pt → normalisé sur 15 (max possible).
    """
    df = df_fixtures.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    points_map = {"W": 3, "D": 1, "L": 0}
    df["points"] = df["result"].map(points_map)

    # Moyenne glissante sur 5 matchs
    df["recent_form"] = (
        df["points"]
        .rolling(window=5, min_periods=1)
        .mean()
        / 3  # normaliser entre 0 et 1
    ).round(4)

    return df


# ─────────────────────────────────────────
# 4. FUSIONNER PLAYERS + LINEUPS + FIXTURES
# ─────────────────────────────────────────

def build_features(df_players, df_lineups, df_fixtures):
    """
    Construit le dataset final pour le modèle ML.
    
    Chaque ligne = un joueur dans un match
    avec ses features + is_starter (variable cible y)
    """

    # Ajouter importance du match et forme récente
    df_fixtures = add_match_importance(df_fixtures)
    df_fixtures = add_recent_form(df_fixtures)

    # Joindre lineups avec fixtures
    df = df_lineups.merge(
        df_fixtures[["fixture_id", "match_importance", "recent_form", "result"]],
        on="fixture_id",
        how="left"
    )

    # Joindre avec stats joueurs
    df = df.merge(
        df_players[[
            "player_name",
            "performance_score", "fatigue_index",
            "defensive_impact", "anomaly_z",
            "rating", "pass_accuracy", "duels_won_pct",
            "goals", "assists", "minutes", "appearances",
        ]],
        on="player_name",
        how="left"
    )

    # Renommer la colonne position pour éviter conflit
    if "position_x" in df.columns:
        df = df.rename(columns={"position_x": "position_match", "position_y": "position_stats"})

    # Remplir les valeurs manquantes
    numeric_cols = [
        "performance_score", "fatigue_index", "defensive_impact",
        "anomaly_z", "rating", "pass_accuracy", "duels_won_pct",
        "goals", "assists", "minutes", "appearances",
        "match_importance", "recent_form"
    ]
    df[numeric_cols] = df[numeric_cols].fillna(0)

    print(f"[FEATURES] Dataset final : {len(df)} lignes, {len(df.columns)} colonnes")
    print(f"[FEATURES] Titulaires : {df['is_starter'].sum()} | Remplaçants : {(df['is_starter'] == 0).sum()}")

    return df


# ─────────────────────────────────────────
# 5. ENCODER LES VARIABLES CATÉGORIELLES
# ─────────────────────────────────────────

def encode_features(df):
    """
    Encode la position en one-hot encoding.
    G=Gardien, D=Défenseur, M=Milieu, F=Attaquant
    """
    df = df.copy()

    position_col = "position_match" if "position_match" in df.columns else "position"

    df["is_goalkeeper"] = (df[position_col] == "G").astype(int)
    df["is_defender"]   = (df[position_col] == "D").astype(int)
    df["is_midfielder"] = (df[position_col] == "M").astype(int)
    df["is_forward"]    = (df[position_col] == "F").astype(int)

    return df


# ─────────────────────────────────────────
# 6. SÉLECTIONNER LES FEATURES FINALES
# ─────────────────────────────────────────

def get_feature_columns():
    """
    Liste des colonnes utilisées comme entrées (X) pour le modèle.
    """
    return [
        "performance_score",
        "fatigue_index",
        "defensive_impact",
        "anomaly_z",
        "rating",
        "pass_accuracy",
        "duels_won_pct",
        "goals",
        "assists",
        "minutes",
        "appearances",
        "match_importance",
        "recent_form",
        "is_goalkeeper",
        "is_defender",
        "is_midfielder",
        "is_forward"
    ]


# ─────────────────────────────────────────
# 7. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_features():
    print("=" * 50)
    print("SMARTLINEUP — Feature Engineering")
    print("=" * 50)

    # Charger les données
    df_players, df_lineups, df_fixtures, df_match_stats = load_data()

    # Construire les features
    df = build_features(df_players, df_lineups, df_fixtures)

    # Encoder les positions
    df = encode_features(df)

    # Afficher un aperçu
    feature_cols = get_feature_columns()
    print(f"\n>>> Features sélectionnées ({len(feature_cols)}) :")
    for col in feature_cols:
        print(f"    - {col}")

    print(f"\n>>> Aperçu du dataset :")
    print(df[feature_cols + ["player_name", "is_starter"]].head(10).to_string())

    # Sauvegarder
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/features.csv", index=False)
    print(f"\n[SAUVEGARDÉ] data/processed/features.csv — {len(df)} lignes")

    print("\n" + "=" * 50)
    print("Feature Engineering terminé !")
    print("=" * 50)

    return df


if __name__ == "__main__":
    run_features()