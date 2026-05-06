# src/analytics/transfer.py

import pandas as pd  # type: ignore[import]
import numpy as np # type: ignore[import]
import os
from pymongo import MongoClient # type: ignore[import]
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import]
from sklearn.preprocessing import StandardScaler # type: ignore[import]
from dotenv import load_dotenv  # type: ignore[import]

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
# 2. PRÉPARER LES FEATURES DE SIMILARITÉ
# ─────────────────────────────────────────

def prepare_similarity_features(df):
    """
    Sélectionne les features qui définissent le style de jeu
    d'un joueur pour calculer la similarité.
    """
    features = [
        "goals",
        "assists",
        "pass_accuracy",
        "duels_won_pct",
        "defensive_impact",
        "rating",
        "minutes",
        "shots_total",
        "passes_key",
        "dribbles_success"
    ]

    # Garder seulement les joueurs avec stats réelles
    df = df[df["rating"] > 0].copy()
    df = df.fillna(0)

    X = df[features]

    # Normaliser
    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return df, X_scaled, features


# ─────────────────────────────────────────
# 3. CALCULER LA SIMILARITÉ COSINUS
# ─────────────────────────────────────────

def calculate_similarity(X_scaled):
    """
    Cosine Similarity : mesure à quel point deux joueurs
    ont un style de jeu similaire.
    
    Score entre 0 et 1 :
    1.0 → joueurs identiques
    0.0 → joueurs complètement différents
    """
    similarity_matrix = cosine_similarity(X_scaled)
    return similarity_matrix


# ─────────────────────────────────────────
# 4. TROUVER LES JOUEURS SIMILAIRES
# ─────────────────────────────────────────

def find_similar_players(df, similarity_matrix, player_name, top_n=5):
    """
    Trouve les joueurs les plus similaires à un joueur donné.
    Utile pour recommander un transfert comme remplaçant.
    """
    df = df.reset_index(drop=True)

    # Trouver l'index du joueur
    matches = df[df["player_name"] == player_name]

    if matches.empty:
        print(f"[ERREUR] Joueur '{player_name}' introuvable.")
        print(f"Joueurs disponibles : {list(df['player_name'].values)}")
        return None

    player_idx = matches.index[0]

    # Scores de similarité
    scores = list(enumerate(similarity_matrix[player_idx]))

    # Trier par similarité décroissante (exclure le joueur lui-même)
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = [(idx, score) for idx, score in scores if idx != player_idx]

    print(f"\n>>> Joueurs similaires à {player_name} :")
    print(f"\n{'Rang':<5} {'Joueur':<25} {'Position':<12} {'Similarité':>12} {'Rating':>8}")
    print("-" * 65)

    similar = []
    for rank, (idx, score) in enumerate(scores[:top_n], 1):
        row = df.iloc[idx]
        print(f"  {rank:<4} {row['player_name']:<25} {row['position']:<12} "
              f"{score:>12.4f} {row['rating']:>8.3f}")
        similar.append({
            "player":     row["player_name"],
            "position":   row["position"],
            "similarity": round(score, 4),
            "rating":     row["rating"]
        })

    return similar


# ─────────────────────────────────────────
# 5. RECOMMANDATION DE TRANSFERT
# ─────────────────────────────────────────

def recommend_transfer(df, similarity_matrix, position=None,
                       min_rating=7.0, budget=50):
    """
    Recommande les meilleurs joueurs à recruter selon :
    - Position recherchée
    - Rating minimum
    - Budget estimé (en millions €)
    """
    df = df.reset_index(drop=True).copy()

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
    df["perf_factor"] = (df["goals"] * 0.5 + df["assists"] * 0.3 + 1)

    # Valeur estimée
    df["estimated_value"] = (
        df["rating"] * df["minutes"] * 0.001 *
        df["age_factor"] * df["pos_factor"] * df["perf_factor"]
    ).round(2)

    # Filtrer selon critères
    filtered = df.copy()

    if position:
        filtered = filtered[filtered["position"] == position]

    filtered = filtered[
        (filtered["rating"] >= min_rating) &
        (filtered["estimated_value"] <= budget)
    ]

    if filtered.empty:
        print(f"[INFO] Aucun joueur trouvé avec ces critères.")
        print(f"       Position={position}, Rating>={min_rating}, Budget<={budget}M€")
        return None

    # Trier par rating décroissant
    filtered = filtered.sort_values("rating", ascending=False)

    print(f"\n{'=' * 70}")
    print(f"  RECOMMANDATIONS DE TRANSFERT")
    print(f"  Position: {position or 'Toutes'} | "
          f"Rating min: {min_rating} | Budget: {budget}M€")
    print(f"{'=' * 70}")

    print(f"\n{'Rang':<5} {'Joueur':<25} {'Position':<12} "
          f"{'Rating':>8} {'Valeur':>10} {'Passes%':>8}")
    print("-" * 72)

    for rank, (_, row) in enumerate(filtered.head(10).iterrows(), 1):
        print(f"  {rank:<4} {row['player_name']:<25} {row['position']:<12} "
              f"{row['rating']:>8.3f} {row['estimated_value']:>8.1f}M€ "
              f"{row['pass_accuracy']:>7.0f}%")

    return filtered.head(10)


# ─────────────────────────────────────────
# 6. ANALYSE DES BESOINS DE L'ÉQUIPE
# ─────────────────────────────────────────

def analyze_team_needs(df, team="Paris Saint Germain"):
    """
    Analyse les points faibles de l'équipe par position
    et recommande quels postes renforcer.
    """
    print(f"\n{'=' * 50}")
    print(f"  ANALYSE DES BESOINS — {team}")
    print(f"{'=' * 50}")

    positions = {
        "Goalkeeper": "Gardien",
        "Defender":   "Défenseur",
        "Midfielder": "Milieu",
        "Forward":    "Attaquant",
        "Attacker":   "Attaquant"
    }

    print(f"\n{'Position':<15} {'Nb joueurs':>10} {'Rating moy':>12} {'Besoin':>10}")
    print("-" * 50)

    needs = []
    for pos, label in positions.items():
        sub = df[df["position"] == pos]
        if sub.empty:
            continue

        nb     = len(sub)
        rating = sub["rating"].mean()
        need   = "🔴 URGENT" if rating < 7.0 else ("🟡 Moyen" if rating < 7.2 else "🟢 OK")

        print(f"  {label:<13} {nb:>10} {rating:>12.3f} {need:>10}")
        needs.append({"position": pos, "avg_rating": rating, "need": need})

    return needs


# ─────────────────────────────────────────
# 7. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_transfer(team="Paris Saint Germain"):
    print("=" * 50)
    print("SMARTLINEUP — Recommandation de Transferts")
    print("=" * 50)

    # Charger
    df = load_players()

    # Préparer features
    df_clean, X_scaled, features = prepare_similarity_features(df)

    # Calculer similarité
    similarity_matrix = calculate_similarity(X_scaled)
    print(f"[SIMILARITÉ] Matrice {similarity_matrix.shape} calculée")

    # Analyser les besoins
    analyze_team_needs(df_clean, team)

    # Trouver joueurs similaires à Mbappé
    find_similar_players(df_clean, similarity_matrix, "Kylian Mbappé")

    # Recommander des transferts par position
    print(f"\n>>> Recommandations pour renforcer la défense :")
    recommend_transfer(
        df_clean, similarity_matrix,
        position="Defender",
        min_rating=7.0,
        budget=100
    )

    print(f"\n>>> Recommandations pour renforcer le milieu :")
    recommend_transfer(
        df_clean, similarity_matrix,
        position="Midfielder",
        min_rating=7.0,
        budget=100
    )

    # Sauvegarder
    os.makedirs("data/processed", exist_ok=True)
    df_clean.to_csv("data/processed/transfer_analysis.csv", index=False)
    print(f"\n[SAUVEGARDÉ] data/processed/transfer_analysis.csv")

    print("\n" + "=" * 50)
    print("Analyse transferts terminée !")
    print("=" * 50)

    return df_clean, similarity_matrix


if __name__ == "__main__":
    run_transfer(team="Paris Saint Germain")