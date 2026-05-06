# src/data_engineering/db.py

import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = "smartlineup"

# ─────────────────────────────────────────
# 1. CONNEXION
# ─────────────────────────────────────────

def get_db():
    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]
    print(f"[CONNECTÉ] MongoDB → base '{DB_NAME}'")
    return db


# ─────────────────────────────────────────
# 2. INSÉRER UN CSV DANS UNE COLLECTION
# ─────────────────────────────────────────

def insert_csv(db, filepath, collection_name):
    if not os.path.exists(filepath):
        print(f"[SKIP] Fichier introuvable : {filepath}")
        return

    df      = pd.read_csv(filepath)
    records = df.to_dict(orient="records")

    collection = db[collection_name]
    collection.drop()                        # Vider avant de réinsérer
    collection.insert_many(records)

    print(f"[INSÉRÉ] {len(records)} documents → collection '{collection_name}'")


# ─────────────────────────────────────────
# 3. CRÉER LES INDEX
# ─────────────────────────────────────────

def create_indexes(db):
    print("\n>>> Création des index...")

    db["fixtures"].create_index("fixture_id", unique=True)
    db["lineups"].create_index([("fixture_id", 1), ("player_id", 1)])
    db["match_stats"].create_index([("fixture_id", 1), ("team", 1)])
    db["players"].create_index("player_id", unique=True)

    print("[OK] Index créés")


# ─────────────────────────────────────────
# 4. VÉRIFIER LES COLLECTIONS
# ─────────────────────────────────────────

def check_db(db):
    print("\n>>> Vérification de la base de données...")
    print(f"{'Collection':<20} {'Documents':>10}")
    print("-" * 32)

    for name in ["fixtures", "lineups", "match_stats", "players"]:
        count = db[name].count_documents({})
        print(f"{name:<20} {count:>10}")


# ─────────────────────────────────────────
# 5. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_db():
    print("=" * 50)
    print("SMARTLINEUP — Chargement base de données")
    print("=" * 50)

    db = get_db()

    insert_csv(db, "data/processed/fixtures_clean.csv",    "fixtures")
    insert_csv(db, "data/processed/lineups_clean.csv",     "lineups")
    insert_csv(db, "data/processed/match_stats_clean.csv", "match_stats")
    insert_csv(db, "data/processed/players_clean.csv",     "players")

    create_indexes(db)
    check_db(db)

    print("\n" + "=" * 50)
    print("Base de données prête !")
    print("=" * 50)


if __name__ == "__main__":
    run_db()