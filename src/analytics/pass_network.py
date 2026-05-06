# src/analytics/pass_network.py

import pandas as pd
import numpy as np
import os
import json
from pymongo import MongoClient
from glob import glob
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


# ─────────────────────────────────────────
# 1. CHARGER LES LINEUPS
# ─────────────────────────────────────────

def load_lineups():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    df     = pd.DataFrame(list(db["lineups"].find({}, {"_id": 0})))
    print(f"[CHARGÉ] {len(df)} entrées lineup")
    return df


# ─────────────────────────────────────────
# 2. CHARGER LES STATS DES JOUEURS
# ─────────────────────────────────────────

def load_players():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    df     = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))
    return df


# ─────────────────────────────────────────
# 3. CONSTRUIRE LE RÉSEAU DE PASSES
# ─────────────────────────────────────────

def build_pass_network(df_lineups, df_players, team="Paris Saint-Germain"):
    """
    Construit un réseau de passes G = (V, E) où :
    V = joueurs titulaires
    E = passes estimées entre joueurs selon leur position et stats
    
    Comme l'API gratuite ne donne pas les passes joueur-à-joueur,
    on estime les connexions selon :
    - La position des joueurs (qui passe à qui logiquement)
    - Le nombre de passes total de chaque joueur
    """

    # Titulaires de l'équipe
    titulaires = df_lineups[
        (df_lineups["team"] == team) &
        (df_lineups["is_starter"] == 1)
    ].copy()

    if titulaires.empty:
        print(f"[ERREUR] Aucun titulaire trouvé pour {team}")
        return None, None

    # Joindre avec les stats
    titulaires = titulaires.merge(
        df_players[["player_name", "passes_total", "passes_key",
                    "pass_accuracy", "position"]],
        on="player_name",
        how="left"
    ).fillna(0)

    titulaires = titulaires.drop_duplicates(subset="player_name")

    print(f"\n[RÉSEAU] {len(titulaires)} joueurs pour {team}")

    # ── Construire les nœuds (V) ──────────────────────────────
    nodes = []
    for _, row in titulaires.iterrows():
        nodes.append({
            "player":   row["player_name"],
            "position": row.get("position_x", row.get("position", "?")),
            "passes":   int(row["passes_total"]),
            "key_passes": int(row["passes_key"]),
            "accuracy": float(row["pass_accuracy"])
        })

    # ── Construire les arêtes (E) ─────────────────────────────
    # Logique tactique : qui passe à qui selon la position
    position_order = {
        "Goalkeeper": 0,
        "Defender":   1,
        "Midfielder": 2,
        "Forward":    3,
        "Attacker":   3
    }

    edges = []
    players_list = titulaires.to_dict(orient="records")

    for i in range(len(players_list)):
        for j in range(len(players_list)):
            if i == j:
                continue

            p1 = players_list[i]
            p2 = players_list[j]

            pos1 = p1.get("position_x", p1.get("position", "Midfielder"))
            pos2 = p2.get("position_x", p2.get("position", "Midfielder"))

            rank1 = position_order.get(pos1, 2)
            rank2 = position_order.get(pos2, 2)

            # Passes vers l'avant ou même ligne
            if rank2 >= rank1:
                passes_p1 = float(p1["passes_total"]) if p1["passes_total"] else 1
                passes_p2 = float(p2["passes_total"]) if p2["passes_total"] else 1

                # Poids de la connexion = moyenne des passes des deux joueurs
                weight = round((passes_p1 + passes_p2) / 2, 2)

                edges.append({
                    "from":   p1["player_name"],
                    "to":     p2["player_name"],
                    "weight": weight
                })

    print(f"[RÉSEAU] {len(nodes)} nœuds | {len(edges)} arêtes")
    return nodes, edges


# ─────────────────────────────────────────
# 4. CENTRALITÉ : JOUEUR CLÉ
# ─────────────────────────────────────────

def calculate_centrality(nodes, edges):
    """
    Calcule la centralité de chaque joueur dans le réseau.
    Centralité = somme des poids des connexions du joueur.
    Le joueur avec la plus haute centralité est le joueur clé.
    """
    centrality = {node["player"]: 0 for node in nodes}

    for edge in edges:
        centrality[edge["from"]] += edge["weight"]
        centrality[edge["to"]]   += edge["weight"]

    # Normaliser entre 0 et 1
    max_val = max(centrality.values()) if centrality else 1
    centrality_norm = {
        player: round(val / max_val, 4)
        for player, val in centrality.items()
    }

    return centrality_norm


# ─────────────────────────────────────────
# 5. AFFICHER LE RÉSEAU
# ─────────────────────────────────────────

def display_network(nodes, edges, centrality, team):
    print(f"\n{'=' * 60}")
    print(f"  RÉSEAU DE PASSES — {team}")
    print(f"{'=' * 60}")

    # Classement par centralité
    sorted_players = sorted(
        centrality.items(),
        key=lambda x: x[1],
        reverse=True
    )

    print(f"\n>>> Centralité des joueurs (joueur clé en tête) :")
    print(f"\n{'Rang':<5} {'Joueur':<25} {'Centralité':>12} {'Rôle':>15}")
    print("-" * 60)

    for i, (player, score) in enumerate(sorted_players, 1):
        # Trouver la position
        node = next((n for n in nodes if n["player"] == player), {})
        pos  = node.get("position", "?")

        bar  = "█" * int(score * 20)
        role = "⭐ JOUEUR CLÉ" if i == 1 else ""

        print(f"  {i:<4} {player:<25} {score:>12.4f}  {bar} {role}")

    # Joueur clé
    key_player = sorted_players[0][0]
    key_node   = next((n for n in nodes if n["player"] == key_player), {})

    print(f"\n{'=' * 60}")
    print(f"  ⭐ JOUEUR CLÉ : {key_player}")
    print(f"     Position   : {key_node.get('position', '?')}")
    print(f"     Passes     : {key_node.get('passes', 0)}")
    print(f"     Passes clés: {key_node.get('key_passes', 0)}")
    print(f"     Précision  : {key_node.get('accuracy', 0)}%")
    print(f"{'=' * 60}")

    # Top connexions
    top_edges = sorted(edges, key=lambda x: x["weight"], reverse=True)[:5]
    print(f"\n>>> Top 5 connexions les plus fortes :")
    print(f"\n{'De':<25} {'Vers':<25} {'Poids':>8}")
    print("-" * 60)
    for edge in top_edges:
        print(f"  {edge['from']:<23} → {edge['to']:<23} {edge['weight']:>8.1f}")


# ─────────────────────────────────────────
# 6. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_pass_network(team="Paris Saint-Germain"):
    print("=" * 50)
    print("SMARTLINEUP — Analyse Réseau de Passes")
    print("=" * 50)

    # Charger
    df_lineups = load_lineups()
    df_players = load_players()

    # Construire le réseau
    nodes, edges = build_pass_network(df_lineups, df_players, team)

    if nodes is None:
        return

    # Calculer la centralité
    centrality = calculate_centrality(nodes, edges)

    # Afficher
    display_network(nodes, edges, centrality, team)

    # Sauvegarder
    os.makedirs("data/processed", exist_ok=True)

    pd.DataFrame(nodes).to_csv(
        "data/processed/pass_network_nodes.csv", index=False
    )
    pd.DataFrame(edges).to_csv(
        "data/processed/pass_network_edges.csv", index=False
    )

    print(f"\n[SAUVEGARDÉ] data/processed/pass_network_nodes.csv")
    print(f"[SAUVEGARDÉ] data/processed/pass_network_edges.csv")

    print("\n" + "=" * 50)
    print("Réseau de passes terminé !")
    print("=" * 50)

    return nodes, edges, centrality


if __name__ == "__main__":
    run_pass_network(team="Paris Saint Germain")