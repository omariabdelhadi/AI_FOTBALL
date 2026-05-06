# src/analytics/tactical.py

import pandas as pd
import numpy as np
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


# ─────────────────────────────────────────
# 1. CHARGER LES DONNÉES
# ─────────────────────────────────────────

def load_data():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]

    df_players = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))
    df_lineups = pd.DataFrame(list(db["lineups"].find({}, {"_id": 0})))
    df_fixtures = pd.DataFrame(list(db["fixtures"].find({}, {"_id": 0})))

    print(f"[CHARGÉ] players={len(df_players)}, lineups={len(df_lineups)}, fixtures={len(df_fixtures)}")
    return df_players, df_lineups, df_fixtures


# ─────────────────────────────────────────
# 2. FORMATIONS DISPONIBLES
# ─────────────────────────────────────────

FORMATIONS = {
    "4-3-3": {
        "Goalkeeper": 1,
        "Defender":   4,
        "Midfielder": 3,
        "Forward":    3
    },
    "4-4-2": {
        "Goalkeeper": 1,
        "Defender":   4,
        "Midfielder": 4,
        "Forward":    2
    },
    "3-5-2": {
        "Goalkeeper": 1,
        "Defender":   3,
        "Midfielder": 5,
        "Forward":    2
    },
    "4-2-3-1": {
        "Goalkeeper": 1,
        "Defender":   4,
        "Midfielder": 5,
        "Forward":    1
    },
    "5-3-2": {
        "Goalkeeper": 1,
        "Defender":   5,
        "Midfielder": 3,
        "Forward":    2
    }
}


# ─────────────────────────────────────────
# 3. TACTICAL FIT PAR FORMATION
# ─────────────────────────────────────────

def calculate_tactical_fit(df_players, formation_name):
    """
    Calcule le TacticalFit de chaque joueur selon la formation.

    TacticalFit = Performance dans formation / Performance moyenne

    Si TacticalFit > 1 → joueur adapté à cette formation
    Si TacticalFit < 1 → joueur moins adapté
    """
    if formation_name not in FORMATIONS:
        print(f"[ERREUR] Formation '{formation_name}' inconnue.")
        return None

    formation  = FORMATIONS[formation_name]
    df         = df_players[df_players["rating"] > 0].copy()
    avg_rating = df["rating"].mean()

    results = []

    for _, row in df.iterrows():
        pos = row["position"]

        # Nombre de joueurs requis à ce poste dans la formation
        # Attacker et Forward sont traités comme Forward
        pos_key = pos if pos in formation else "Forward"
        slots   = formation.get(pos_key, 0)

        # Score tactique = rating × (slots / total joueurs du poste)
        pos_count = len(df[df["position"] == pos])
        pos_count = max(pos_count, 1)

        tactical_score = row["rating"] * (slots / pos_count)

        # TacticalFit = performance dans formation / performance moyenne
        tactical_fit = round(tactical_score / avg_rating, 4)

        results.append({
            "player_name":   row["player_name"],
            "position":      pos,
            "rating":        row["rating"],
            "tactical_score": round(tactical_score, 4),
            "tactical_fit":  tactical_fit,
            "formation":     formation_name
        })

    return pd.DataFrame(results)


# ─────────────────────────────────────────
# 4. MEILLEURE FORMATION POUR L'ÉQUIPE
# ─────────────────────────────────────────

def find_best_formation(df_players):
    """
    Teste toutes les formations et trouve celle qui
    maximise le TacticalFit global de l'équipe.
    """
    print(f"\n{'=' * 55}")
    print(f"  ANALYSE TACTIQUE — Meilleure Formation")
    print(f"{'=' * 55}")

    formation_scores = {}

    for formation_name in FORMATIONS:
        df_fit = calculate_tactical_fit(df_players, formation_name)
        if df_fit is None:
            continue

        avg_fit = df_fit["tactical_fit"].mean()
        formation_scores[formation_name] = round(avg_fit, 4)

    # Trier par score
    sorted_formations = sorted(
        formation_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    print(f"\n{'Formation':<12} {'TacticalFit moy':>16} {'Adapté ?':>10}")
    print("-" * 42)

    for i, (name, score) in enumerate(sorted_formations):
        bar      = "█" * int(score * 20)
        best_tag = "⭐ MEILLEURE" if i == 0 else ""
        print(f"  {name:<10} {score:>16.4f}  {bar} {best_tag}")

    best_formation = sorted_formations[0][0]
    print(f"\n  → Formation recommandée : {best_formation}")

    return best_formation, formation_scores


# ─────────────────────────────────────────
# 5. LINEUP OPTIMAL POUR UNE FORMATION
# ─────────────────────────────────────────

def build_optimal_lineup(df_players, formation_name):
    """
    Sélectionne les meilleurs joueurs pour chaque
    poste selon la formation choisie.
    """
    formation = FORMATIONS[formation_name]
    df        = df_players[df_players["rating"] > 0].copy()

    print(f"\n{'=' * 55}")
    print(f"  LINEUP OPTIMAL — {formation_name}")
    print(f"{'=' * 55}")

    selected   = []
    used_players = set()

    pos_labels = {
        "Goalkeeper": "🧤 Gardien",
        "Defender":   "🛡️  Défenseur",
        "Midfielder": "⚙️  Milieu",
        "Forward":    "⚡ Attaquant",
        "Attacker":   "⚡ Attaquant"
    }

    for pos, slots in formation.items():
        # Joueurs disponibles à ce poste
        available = df[
            (df["position"] == pos) &
            (~df["player_name"].isin(used_players))
        ].sort_values("rating", ascending=False)

        # Si pas assez de joueurs → prendre Attacker aussi pour Forward
        if len(available) < slots and pos == "Forward":
            available = df[
                (df["position"].isin(["Forward", "Attacker"])) &
                (~df["player_name"].isin(used_players))
            ].sort_values("rating", ascending=False)

        chosen = available.head(slots)

        print(f"\n  {pos_labels.get(pos, pos)} (×{slots}) :")
        for _, row in chosen.iterrows():
            print(f"    ✓ {row['player_name']:<25} rating={row['rating']:.3f}")
            used_players.add(row["player_name"])
            selected.append({
                "player_name": row["player_name"],
                "position":    pos,
                "rating":      row["rating"],
                "formation":   formation_name
            })

    return pd.DataFrame(selected)


# ─────────────────────────────────────────
# 6. ANALYSE PAR FORMATION
# ─────────────────────────────────────────

def analyze_formation(df_players, formation_name):
    """
    Analyse détaillée d'une formation spécifique.
    """
    df_fit = calculate_tactical_fit(df_players, formation_name)
    if df_fit is None:
        return

    print(f"\n{'=' * 60}")
    print(f"  ANALYSE FORMATION {formation_name}")
    print(f"{'=' * 60}")

    # Top joueurs par TacticalFit
    df_fit = df_fit.sort_values("tactical_fit", ascending=False)

    print(f"\n{'Joueur':<25} {'Position':<12} {'Rating':>8} {'TacticalFit':>12}")
    print("-" * 60)

    for _, row in df_fit.head(11).iterrows():
        fit_bar = "█" * int(row["tactical_fit"] * 10)
        print(f"  {row['player_name']:<23} {row['position']:<12} "
              f"{row['rating']:>8.3f} {row['tactical_fit']:>12.4f} {fit_bar}")

    return df_fit


# ─────────────────────────────────────────
# 7. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_tactical(team="Paris Saint Germain"):
    print("=" * 50)
    print("SMARTLINEUP — Analyse Tactique")
    print("=" * 50)

    # Charger
    df_players, df_lineups, df_fixtures = load_data()

    # Garder joueurs avec stats
    df_clean = df_players[df_players["rating"] > 0].copy()
    print(f"[FILTRÉ] {len(df_clean)} joueurs avec stats")

    # Trouver la meilleure formation
    best_formation, scores = find_best_formation(df_clean)

    # Analyser la meilleure formation en détail
    analyze_formation(df_clean, best_formation)

    # Construire le lineup optimal
    df_lineup = build_optimal_lineup(df_clean, best_formation)

    # Sauvegarder
    os.makedirs("data/processed", exist_ok=True)
    df_lineup.to_csv("data/processed/tactical_lineup.csv", index=False)
    print(f"\n[SAUVEGARDÉ] data/processed/tactical_lineup.csv")

    print("\n" + "=" * 50)
    print("Analyse tactique terminée !")
    print("=" * 50)

    return df_lineup, best_formation


if __name__ == "__main__":
    run_tactical(team="Paris Saint Germain")