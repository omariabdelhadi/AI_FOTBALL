# src/machine_learning/anomaly.py

import pandas as pd
import numpy as np
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


# ─────────────────────────────────────────
# 1. CHARGER LES JOUEURS
# ─────────────────────────────────────────

def load_players():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    df     = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))
    print(f"[CHARGÉ] {len(df)} joueurs")
    return df


# ─────────────────────────────────────────
# 2. CALCUL DU Z-SCORE
# ─────────────────────────────────────────

def calculate_zscore(df, column):
    """
    Z = (X - moyenne) / écart_type
    
    Si Z > 2  → joueur surperforme (anormalement bon)
    Si Z < -2 → joueur sous-performe (anormalement mauvais)
    """
    mean = df[column].mean()
    std  = df[column].std()

    if std == 0:
        return pd.Series([0] * len(df), index=df.index)

    return ((df[column] - mean) / std).round(4)


# ─────────────────────────────────────────
# 3. DÉTECTER LES ANOMALIES
# ─────────────────────────────────────────

def detect_anomalies(df):
    """
    Calcule les Z-scores sur plusieurs métriques
    et détecte les joueurs anormaux.
    """
    df = df.copy()

    # Z-scores sur les métriques clés
    df["z_rating"]            = calculate_zscore(df, "rating")
    df["z_performance_score"] = calculate_zscore(df, "performance_score")
    df["z_goals"]             = calculate_zscore(df, "goals")
    df["z_pass_accuracy"]     = calculate_zscore(df, "pass_accuracy")
    df["z_defensive_impact"]  = calculate_zscore(df, "defensive_impact")

    # Score d'anomalie global = moyenne des Z-scores absolus
    df["anomaly_score"] = (
        df[["z_rating", "z_performance_score", "z_goals",
            "z_pass_accuracy", "z_defensive_impact"]]
        .abs()
        .mean(axis=1)
        .round(4)
    )

    # Classifier l'anomalie
    def classify(row):
        if row["anomaly_score"] < 1:
            return "Normal"
        elif row["z_rating"] > 2 or row["z_performance_score"] > 2:
            return "Surperformance"
        elif row["z_rating"] < -2 or row["z_performance_score"] < -2:
            return "Sous-performance"
        else:
            return "Attention"

    df["anomaly_type"] = df.apply(classify, axis=1)

    return df


# ─────────────────────────────────────────
# 4. AFFICHER LES RÉSULTATS
# ─────────────────────────────────────────

def display_anomalies(df):

    # Joueurs normaux
    normal = df[df["anomaly_type"] == "Normal"]

    # Joueurs en surperformance
    surperf = df[df["anomaly_type"] == "Surperformance"]\
        .sort_values("anomaly_score", ascending=False)

    # Joueurs en sous-performance
    sousperf = df[df["anomaly_type"] == "Sous-performance"]\
        .sort_values("anomaly_score", ascending=False)

    # Joueurs à surveiller
    attention = df[df["anomaly_type"] == "Attention"]\
        .sort_values("anomaly_score", ascending=False)

    print(f"\n{'=' * 60}")
    print(f"  DÉTECTION D'ANOMALIES")
    print(f"{'=' * 60}")
    print(f"  Total joueurs  : {len(df)}")
    print(f"  Normaux        : {len(normal)}")
    print(f"  Surperformance : {len(surperf)}")
    print(f"  Sous-perf      : {len(sousperf)}")
    print(f"  Attention      : {len(attention)}")
    print(f"{'=' * 60}")

    # Surperformance
    if len(surperf) > 0:
        print(f"\n🌟 JOUEURS EN SURPERFORMANCE :")
        print(f"{'Joueur':<25} {'Rating':>8} {'Perf.Score':>12} {'Z-Score':>9}")
        print("-" * 58)
        for _, row in surperf.iterrows():
            print(f"  {row['player_name']:<23} {row['rating']:>8.3f} "
                  f"{row['performance_score']:>12.4f} {row['anomaly_score']:>9.4f}")

    # Sous-performance
    if len(sousperf) > 0:
        print(f"\n⚠️  JOUEURS EN SOUS-PERFORMANCE :")
        print(f"{'Joueur':<25} {'Rating':>8} {'Perf.Score':>12} {'Z-Score':>9}")
        print("-" * 58)
        for _, row in sousperf.iterrows():
            print(f"  {row['player_name']:<23} {row['rating']:>8.3f} "
                  f"{row['performance_score']:>12.4f} {row['anomaly_score']:>9.4f}")

    # Attention
    if len(attention) > 0:
        print(f"\n👀 JOUEURS À SURVEILLER :")
        print(f"{'Joueur':<25} {'Rating':>8} {'Perf.Score':>12} {'Z-Score':>9}")
        print("-" * 58)
        for _, row in attention.iterrows():
            print(f"  {row['player_name']:<23} {row['rating']:>8.3f} "
                  f"{row['performance_score']:>12.4f} {row['anomaly_score']:>9.4f}")

    return surperf, sousperf, attention


# ─────────────────────────────────────────
# 5. RAPPORT PAR POSITION
# ─────────────────────────────────────────

def anomaly_by_position(df):
    print(f"\n>>> Anomalies par position :")
    print(f"{'Position':<15} {'Normal':>8} {'Surperf':>8} {'Sous-perf':>10} {'Attention':>10}")
    print("-" * 55)

    for pos in ["Goalkeeper", "Defender", "Midfielder", "Attacker", "Forward"]:
        pos_labels = {
            "Goalkeeper": "Gardien",
            "Defender":   "Défenseur",
            "Midfielder": "Milieu",
            "Attacker":   "Attaquant",
            "Forward":    "Attaquant"
        }
        sub = df[df["position"] == pos]
        if len(sub) == 0:
            continue

        n  = len(sub[sub["anomaly_type"] == "Normal"])
        s  = len(sub[sub["anomaly_type"] == "Surperformance"])
        sp = len(sub[sub["anomaly_type"] == "Sous-performance"])
        a  = len(sub[sub["anomaly_type"] == "Attention"])

        print(f"  {pos_labels.get(pos, pos):<13} {n:>8} {s:>8} {sp:>10} {a:>10}")


# ─────────────────────────────────────────
# 6. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_anomaly():
    print("=" * 50)
    print("SMARTLINEUP — Détection d'Anomalies")
    print("=" * 50)

    # Charger
    df = load_players()

    # Garder seulement les joueurs avec des stats réelles
    df = df[df["rating"] > 0].copy()
    print(f"[FILTRÉ] {len(df)} joueurs avec stats réelles")

    # Détecter les anomalies
    df = detect_anomalies(df)

    # Afficher
    surperf, sousperf, attention = display_anomalies(df)

    # Par position
    anomaly_by_position(df)

    # Sauvegarder
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/anomalies.csv", index=False)
    print(f"\n[SAUVEGARDÉ] data/processed/anomalies.csv")

    print("\n" + "=" * 50)
    print("Détection d'anomalies terminée !")
    print("=" * 50)

    return df


if __name__ == "__main__":
    run_anomaly()