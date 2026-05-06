# src/data_engineering/clean.py

import json
import os
import pandas as pd
import numpy as np
from glob import glob

# ─────────────────────────────────────────
# 1. CHARGER UN FICHIER JSON
# ─────────────────────────────────────────

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_csv(df, filename):
    os.makedirs("data/processed", exist_ok=True)
    path = f"data/processed/{filename}"
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"[SAUVEGARDÉ] {path} — {len(df)} lignes")


# ─────────────────────────────────────────
# 2. NETTOYER LES MATCHS (FIXTURES)
# ─────────────────────────────────────────

def clean_fixtures():
    print("\n>>> Nettoyage des matchs...")

    files = glob("data/raw/fixtures_team*.json")
    if not files:
        print("[SKIP] Aucun fichier fixtures trouvé.")
        return None

    all_fixtures = []

    for filepath in files:
        data = load_json(filepath)

        for match in data:
            all_fixtures.append({
                "fixture_id":   match["fixture"]["id"],
                "date":         match["fixture"]["date"],
                "venue":        match["fixture"]["venue"]["name"],
                "home_team":    match["teams"]["home"]["name"],
                "away_team":    match["teams"]["away"]["name"],
                "home_goals":   match["goals"]["home"],
                "away_goals":   match["goals"]["away"],
                "result":       (
                    "W" if match["teams"]["home"]["winner"] else
                    "L" if match["teams"]["away"]["winner"] else "D"
                )
            })

    df = pd.DataFrame(all_fixtures)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.drop_duplicates(subset="fixture_id")

    save_csv(df, "fixtures_clean.csv")
    return df


# ─────────────────────────────────────────
# 3. NETTOYER LES LINEUPS
# ─────────────────────────────────────────

def clean_lineups():
    print("\n>>> Nettoyage des lineups...")

    files = glob("data/raw/lineup_fixture*.json")
    if not files:
        print("[SKIP] Aucun fichier lineup trouvé.")
        return None

    all_lineups = []

    for filepath in files:
        fixture_id = filepath.split("lineup_fixture")[1].replace(".json", "")
        data = load_json(filepath)

        for team_data in data:
            team_name = team_data["team"]["name"]

            for player in team_data["startXI"]:
                all_lineups.append({
                    "fixture_id":  int(fixture_id),
                    "team":        team_name,
                    "player_id":   player["player"]["id"],
                    "player_name": player["player"]["name"],
                    "position":    player["player"]["pos"],
                    "grid":        player["player"]["grid"],
                    "is_starter":  1
                })

            for player in team_data["substitutes"]:
                all_lineups.append({
                    "fixture_id":  int(fixture_id),
                    "team":        team_name,
                    "player_id":   player["player"]["id"],
                    "player_name": player["player"]["name"],
                    "position":    player["player"]["pos"],
                    "grid":        None,
                    "is_starter":  0
                })

    df = pd.DataFrame(all_lineups)
    df = df.drop_duplicates(subset=["fixture_id", "player_id"])
    df = df.fillna({"position": "Unknown", "grid": "0-0"})

    save_csv(df, "lineups_clean.csv")
    return df


# ─────────────────────────────────────────
# 4. NETTOYER LES STATS DES MATCHS
# ─────────────────────────────────────────

def clean_match_stats():
    print("\n>>> Nettoyage des stats des matchs...")

    files = glob("data/raw/stats_fixture*.json")
    if not files:
        print("[SKIP] Aucun fichier stats trouvé.")
        return None

    all_stats = []

    for filepath in files:
        fixture_id = filepath.split("stats_fixture")[1].replace(".json", "")
        data = load_json(filepath)

        for team_data in data:
            row = {
                "fixture_id": int(fixture_id),
                "team":       team_data["team"]["name"]
            }

            for stat in team_data["statistics"]:
                key = stat["type"].lower().replace(" ", "_")
                value = stat["value"]

                if isinstance(value, str) and "%" in value:
                    value = float(value.replace("%", ""))
                elif value is None:
                    value = 0

                row[key] = value

            all_stats.append(row)

    df = pd.DataFrame(all_stats)
    df = df.drop_duplicates(subset=["fixture_id", "team"])
    df = df.fillna(0)

    save_csv(df, "match_stats_clean.csv")
    return df


# ─────────────────────────────────────────
# 5. NETTOYER LES STATS JOUEURS (KAGGLE)
# ─────────────────────────────────────────

def clean_player_stats_kaggle():
    print("\n>>> Nettoyage des stats joueurs (Kaggle)...")

    kaggle_path = "data/external/players_stats.csv"
    if not os.path.exists(kaggle_path):
        print("[SKIP] Fichier Kaggle introuvable.")
        return None

    from unidecode import unidecode
    df = pd.read_csv(kaggle_path, encoding="latin-1", sep=";", on_bad_lines="skip")
    df["Player"] = df["Player"].apply(lambda x: unidecode(str(x)))

    # Mapper les positions
    def map_position(pos):
        if pd.isna(pos):
            return "Unknown"
        pos = str(pos).upper()
        if "GK" in pos:
            return "Goalkeeper"
        elif "DF" in pos:
            return "Defender"
        elif "MF" in pos:
            return "Midfielder"
        elif "FW" in pos or "AT" in pos:
            return "Forward"
        else:
            return "Midfielder"

    df["position"] = df["Pos"].apply(map_position)

    # Renommer les colonnes
    df = df.rename(columns={
        "Player":       "player_name",
        "Squad":        "team",
        "Comp":         "league",
        "Age":          "age",
        "Min":          "minutes",
        "Goals":        "goals",
        "Assists":      "assists",
        "PasTotCmp%":   "pass_accuracy",
        "PasTotCmp":    "passes_total",
        "PasAss":       "passes_key",
        "Tkl":          "tackles",
        "Int":          "interceptions",
        "Blocks":       "blocks",
        "ToAtt":        "dribbles_attempts",
        "ToSuc":        "dribbles_success",
        "Fld":          "fouls_drawn",
        "Fls":          "fouls_committed",
        "CrdY":         "yellow_cards",
        "CrdR":         "red_cards",
        "SoT":          "shots_on",
        "Shots":        "shots_total",
        "MP":           "appearances",
        "Starts":       "starts",
    })

    # Sélectionner les colonnes utiles
    cols = [
        "player_name", "team", "league", "age", "position",
        "appearances", "starts", "minutes",
        "goals", "assists", "shots_total", "shots_on",
        "passes_total", "passes_key", "pass_accuracy",
        "tackles", "interceptions", "blocks",
        "dribbles_attempts", "dribbles_success",
        "fouls_drawn", "fouls_committed",
        "yellow_cards", "red_cards"
    ]

    df = df[cols].copy()
    df = df.fillna(0)

    # Convertir en numérique
    numeric_cols = cols[5:]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Ajouter player_id unique
    df["player_id"] = range(1, len(df) + 1)

    # ── Calculer les indices du projet ──────────────

    # Rating proxy (basé sur les stats disponibles)
    df["rating"] = (
        7.0
        + df["goals"]        * 0.1
        + df["assists"]      * 0.07
        + (df["pass_accuracy"] / 100) * 0.5
        - df["yellow_cards"] * 0.05
        - df["red_cards"]    * 0.2
    ).clip(5.0, 10.0).round(3)

    # Duels won %
    df["duels_won_pct"] = np.where(
        df["dribbles_attempts"] > 0,
        df["dribbles_success"] / df["dribbles_attempts"],
        0
    ).round(4)

    # xG proxy
    df["xg_proxy"] = np.where(
        df["appearances"] > 0,
        df["goals"] / df["appearances"],
        0
    )

    # Performance Score
    df["performance_score"] = (
        0.3 * df["xg_proxy"] +
        0.2 * (df["pass_accuracy"] / 100) +
        0.2 * df["duels_won_pct"] +
        0.3 * (df["rating"] / 10)
    ).round(4)

    # Fatigue Index
    df["fatigue_index"] = np.where(
        df["appearances"] > 0,
        (df["minutes"] / df["appearances"]) / 90,
        0
    ).round(4)

    # Defensive Impact
    df["defensive_impact"] = (
        0.4 * df["tackles"] +
        0.3 * df["interceptions"] +
        0.3 * df["blocks"]
    ).round(4)

    # Anomaly Z-score
    mean_ps = df["performance_score"].mean()
    std_ps  = df["performance_score"].std()
    df["anomaly_z"] = np.where(
        std_ps > 0,
        (df["performance_score"] - mean_ps) / std_ps,
        0
    ).round(4)
    df["is_anomaly"] = (df["anomaly_z"].abs() > 2).astype(int)

    print(f"[INFO] {len(df)} joueurs | {df['team'].nunique()} équipes | {df['league'].nunique()} ligues")
    print(f"[INFO] Ligues : {df['league'].unique()}")

    save_csv(df, "players_clean.csv")
    return df


# ─────────────────────────────────────────
# 6. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_cleaning():
    print("=" * 50)
    print("SMARTLINEUP — Nettoyage démarré")
    print("=" * 50)

    df_fixtures    = clean_fixtures()
    df_lineups     = clean_lineups()
    df_match_stats = clean_match_stats()
    df_players     = clean_player_stats_kaggle()

    print("\n" + "=" * 50)
    print("Nettoyage terminé. Fichiers dans data/processed/")
    print("=" * 50)

    return df_fixtures, df_lineups, df_match_stats, df_players


if __name__ == "__main__":
    run_cleaning()