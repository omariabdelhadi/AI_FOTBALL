# src/data_engineering/collect.py

import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# ─────────────────────────────────────────
# 1. FONCTION DE BASE : appel API générique
# ─────────────────────────────────────────

def api_get(endpoint, params={}):
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()

        if data["errors"]:
            print(f"[ERREUR API] {data['errors']}")
            return None

        print(f"[OK] {endpoint} → {data['results']} résultat(s)")
        return data["response"]

    except requests.exceptions.RequestException as e:
        print(f"[ERREUR REQUÊTE] {e}")
        return None


# ─────────────────────────────────────────
# 2. SAUVEGARDER EN JSON
# ─────────────────────────────────────────

def save_json(data, filename):
    os.makedirs("data/raw", exist_ok=True)
    path = f"data/raw/{filename}"
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"[SAUVEGARDÉ] {path}")


# ─────────────────────────────────────────
# 3. COLLECTER LES ÉQUIPES D'UNE LIGUE
# ─────────────────────────────────────────

def collect_teams(league_id, season):
    print(f"\n>>> Collecte des équipes (ligue={league_id}, saison={season})")
    
    data = api_get("teams", params={
        "league": league_id,
        "season": season
    })

    if data:
        save_json(data, f"teams_league{league_id}_season{season}.json")
    
    return data


# ─────────────────────────────────────────
# 4. COLLECTER LES MATCHS D'UNE ÉQUIPE
# ─────────────────────────────────────────

def collect_fixtures(team_id, season):
    print(f"\n>>> Collecte des matchs (équipe={team_id}, saison={season})")
    
    data = api_get("fixtures", params={
        "team": team_id,
        "season": season,
        "status": "FT"
    })

    if data:
        save_json(data, f"fixtures_team{team_id}_season{season}.json")
    
    return data


# ─────────────────────────────────────────
# 5. COLLECTER LES STATS D'UN MATCH
# ─────────────────────────────────────────

def collect_match_stats(fixture_id):
    print(f"\n>>> Collecte des stats du match {fixture_id}")
    
    data = api_get("fixtures/statistics", params={
        "fixture": fixture_id
    })

    if data:
        save_json(data, f"stats_fixture{fixture_id}.json")
    
    return data


# ─────────────────────────────────────────
# 6. COLLECTER LES STATS DES JOUEURS
# ─────────────────────────────────────────

def collect_player_stats(team_id, season):
    print(f"\n>>> Collecte des stats joueurs (équipe={team_id}, saison={season})")
    
    all_players = []
    page = 1

    while True:
        data = api_get("players", params={
            "team": team_id,
            "season": season,
            "page": page
        })

        if not data:
            break

        all_players.extend(data)
        
        if len(data) < 20:
            break
        
        page += 1
        time.sleep(7)

    if all_players:
        save_json(all_players, f"players_team{team_id}_season{season}.json")
    
    return all_players


# ─────────────────────────────────────────
# 7. COLLECTER LE LINEUP D'UN MATCH
# ─────────────────────────────────────────

def collect_lineup(fixture_id):
    print(f"\n>>> Collecte du lineup du match {fixture_id}")
    
    data = api_get("fixtures/lineups", params={
        "fixture": fixture_id
    })

    if data:
        save_json(data, f"lineup_fixture{fixture_id}.json")
    
    return data


# ─────────────────────────────────────────
# 8. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_collection(league_id=61, season=2023, team_id=85, nb_matchs=10):
    print("=" * 50)
    print(f"SMARTLINEUP — Collecte démarrée : {datetime.now()}")
    print("=" * 50)

    # Étape 1 : équipes de la ligue
    collect_teams(league_id, season)
    time.sleep(7)

    # Étape 2 : matchs terminés de l'équipe
    fixtures = collect_fixtures(team_id, season)
    time.sleep(7)

    if not fixtures:
        print("[STOP] Aucun match trouvé.")
        return

    # Étape 3 : pour chaque match (limité à nb_matchs) → stats + lineup
    print(f"\n>>> Traitement de {nb_matchs} matchs sur {len(fixtures)} disponibles")
    
    for match in fixtures[:nb_matchs]:
        fixture_id = match["fixture"]["id"]

        collect_match_stats(fixture_id)
        time.sleep(7)

        collect_lineup(fixture_id)
        time.sleep(7)

    # Étape 4 : stats individuelles des joueurs
    collect_player_stats(team_id, season)

    print("\n" + "=" * 50)
    print("Collecte terminée. Fichiers dans data/raw/")
    print("=" * 50)


# ─────────────────────────────────────────
# EXÉCUTION DIRECTE
# ─────────────────────────────────────────

if __name__ == "__main__":
    run_collection(
        league_id=61,   # Ligue 1
        season=2023,    # Saison 2023/2024
        team_id=85,     # PSG
        nb_matchs=10    # Nombre de matchs à traiter
    )