# src/visualization/charts.py

import pandas as pd
import numpy as np
import os
import pickle
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


# ─────────────────────────────────────────
# 1. CHARGER LES DONNÉES
# ─────────────────────────────────────────

def load_data():
    client     = MongoClient(MONGO_URI)
    db         = client["smartlineup"]
    df_players = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))
    df_lineups = pd.DataFrame(list(db["lineups"].find({}, {"_id": 0})))
    df_fixtures= pd.DataFrame(list(db["fixtures"].find({}, {"_id": 0})))
    return df_players, df_lineups, df_fixtures


# ─────────────────────────────────────────
# 2. GRAPHIQUE : PERFORMANCE DES JOUEURS
# ─────────────────────────────────────────

def chart_player_performance(df_players):
    df = df_players[df_players["rating"] > 0].copy()
    df = df.sort_values("rating", ascending=True).tail(15)

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    colors = ["#00d4aa" if r >= 7.3 else "#f39c12" if r >= 7.0
              else "#e74c3c" for r in df["rating"]]

    bars = ax.barh(df["player_name"], df["rating"], color=colors, height=0.6)

    # Valeurs sur les barres
    for bar, val in zip(bars, df["rating"]):
        ax.text(val + 0.01, bar.get_y() + bar.get_height()/2,
                f"{val:.2f}", va="center", color="white", fontsize=9)

    ax.set_xlabel("Rating", color="white")
    ax.set_title("⭐ Performance des Joueurs", color="white",
                 fontsize=14, fontweight="bold", pad=15)
    ax.tick_params(colors="white")
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.set_xlim(6.0, 8.5)

    # Légende
    legend = [
        mpatches.Patch(color="#00d4aa", label="Excellent (≥7.3)"),
        mpatches.Patch(color="#f39c12", label="Bon (≥7.0)"),
        mpatches.Patch(color="#e74c3c", label="Faible (<7.0)")
    ]
    ax.legend(handles=legend, facecolor="#1a1a2e", labelcolor="white")

    plt.tight_layout()
    os.makedirs("data/processed", exist_ok=True)
    plt.savefig("data/processed/chart_performance.png", dpi=150,
                bbox_inches="tight", facecolor="#0d1117")
    print("[SAUVEGARDÉ] chart_performance.png")
    plt.close()


# ─────────────────────────────────────────
# 3. GRAPHIQUE : RÉSULTATS DES MATCHS
# ─────────────────────────────────────────

def chart_match_results(df_fixtures):
    counts = df_fixtures["result"].value_counts()

    labels = {"W": "Victoire", "D": "Nul", "L": "Défaite"}
    colors = {"W": "#00d4aa", "D": "#f39c12", "L": "#e74c3c"}

    fig, ax = plt.subplots(figsize=(7, 7))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=[labels.get(k, k) for k in counts.index],
        colors=[colors.get(k, "#888") for k in counts.index],
        autopct="%1.1f%%",
        startangle=90,
        textprops={"color": "white", "fontsize": 12}
    )

    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(11)

    ax.set_title("📊 Résultats des Matchs", color="white",
                 fontsize=14, fontweight="bold", pad=15)

    plt.tight_layout()
    plt.savefig("data/processed/chart_results.png", dpi=150,
                bbox_inches="tight", facecolor="#0d1117")
    print("[SAUVEGARDÉ] chart_results.png")
    plt.close()


# ─────────────────────────────────────────
# 4. GRAPHIQUE : ANOMALIES
# ─────────────────────────────────────────

def chart_anomalies(df_players):
    df = df_players[df_players["rating"] > 0].copy()

    mean_ps = df["performance_score"].mean()
    std_ps  = df["performance_score"].std()
    df["z"] = (df["performance_score"] - mean_ps) / std_ps

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    colors = []
    for z in df["z"]:
        if z > 2:
            colors.append("#00d4aa")
        elif z < -2:
            colors.append("#e74c3c")
        else:
            colors.append("#4a9eff")

    ax.bar(range(len(df)), df["z"], color=colors, width=0.7)

    # Lignes seuil
    ax.axhline(y=2,  color="#00d4aa", linestyle="--", alpha=0.7, label="Seuil +2")
    ax.axhline(y=-2, color="#e74c3c", linestyle="--", alpha=0.7, label="Seuil -2")
    ax.axhline(y=0,  color="white",   linestyle="-",  alpha=0.3)

    # Noms des joueurs
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["player_name"], rotation=45, ha="right",
                       color="white", fontsize=8)

    ax.set_ylabel("Z-Score", color="white")
    ax.set_title("🔍 Détection d'Anomalies", color="white",
                 fontsize=14, fontweight="bold", pad=15)
    ax.tick_params(colors="white")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(facecolor="#1a1a2e", labelcolor="white")

    plt.tight_layout()
    plt.savefig("data/processed/chart_anomalies.png", dpi=150,
                bbox_inches="tight", facecolor="#0d1117")
    print("[SAUVEGARDÉ] chart_anomalies.png")
    plt.close()


# ─────────────────────────────────────────
# 5. GRAPHIQUE : RÉSEAU DE PASSES
# ─────────────────────────────────────────

def chart_pass_network():
    nodes_path = "data/processed/pass_network_nodes.csv"
    edges_path = "data/processed/pass_network_edges.csv"

    if not os.path.exists(nodes_path):
        print("[SKIP] Lance d'abord pass_network.py")
        return

    df_nodes = pd.read_csv(nodes_path)
    df_edges = pd.read_csv(edges_path)

    # Garder seulement top 11 joueurs par passes
    df_nodes = df_nodes.head(11).reset_index(drop=True)
    top_players = set(df_nodes["player"].values)

    fig, ax = plt.subplots(figsize=(9, 12))
    fig.patch.set_facecolor("#1a6b1a")
    ax.set_facecolor("#1a6b1a")

    # Terrain
    ax.add_patch(plt.Rectangle((0.05, 0.02), 0.9, 0.96,
                 fill=False, edgecolor="white", linewidth=2))
    ax.axhline(y=0.5, color="white", linewidth=1.5, alpha=0.5)
    ax.add_patch(plt.Circle((0.5, 0.5), 0.1,
                 fill=False, edgecolor="white", linewidth=1.5, alpha=0.5))

    # Position Y par poste
    pos_y = {
        "Goalkeeper": 0.08,
        "Defender":   0.28,
        "Midfielder": 0.58,
        "Forward":    0.82,
        "Attacker":   0.82,
        "G": 0.08, "D": 0.28, "M": 0.58, "F": 0.82
    }

    # Grouper par position pour espacer en X
    pos_groups = {}
    for _, row in df_nodes.iterrows():
        pos = str(row["position"])
        if pos not in pos_groups:
            pos_groups[pos] = []
        pos_groups[pos].append(row["player"])

    # Calculer les coordonnées
    coords = {}
    for pos, players in pos_groups.items():
        n   = len(players)
        y   = pos_y.get(pos, 0.5)
        xs  = np.linspace(0.15, 0.85, n)
        for i, player in enumerate(players):
            coords[player] = (xs[i], y)

    # Arêtes top 12
    top_edges = df_edges[
        df_edges["from"].isin(top_players) &
        df_edges["to"].isin(top_players)
    ].nlargest(12, "weight")

    max_w = top_edges["weight"].max() if len(top_edges) > 0 else 1

    for _, edge in top_edges.iterrows():
        if edge["from"] in coords and edge["to"] in coords:
            x1, y1 = coords[edge["from"]]
            x2, y2 = coords[edge["to"]]
            alpha  = edge["weight"] / max_w * 0.7
            lw     = edge["weight"] / max_w * 4
            ax.plot([x1, x2], [y1, y2],
                    color="#00d4aa", alpha=alpha, linewidth=lw)

    # Nœuds
    for _, row in df_nodes.iterrows():
        if row["player"] not in coords:
            continue
        x, y  = coords[row["player"]]
        size  = 400 + row["passes"] * 0.05
        ax.scatter(x, y, s=size, color="#00d4aa",
                   zorder=5, edgecolors="white", linewidth=2)
        name = row["player"].split()[-1]
        ax.text(x, y - 0.05, name, ha="center",
                color="white", fontsize=9, fontweight="bold")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("🔗 Réseau de Passes — 11 Titulaires",
                 color="white", fontsize=14, fontweight="bold", pad=15)

    plt.tight_layout()
    plt.savefig("data/processed/chart_pass_network.png", dpi=150,
                bbox_inches="tight", facecolor="#1a6b1a")
    print("[SAUVEGARDÉ] chart_pass_network.png")
    plt.close()


# ─────────────────────────────────────────
# 6. GRAPHIQUE : RADAR D'UN JOUEUR
# ─────────────────────────────────────────

def chart_player_radar(df_players, player_name="Vitinha"):
    df = df_players[df_players["rating"] > 0].copy()
    player = df[df["player_name"] == player_name]

    if player.empty:
        print(f"[SKIP] Joueur '{player_name}' introuvable")
        return

    player = player.iloc[0]

    categories = ["Rating", "Passes%", "Duels%",
                  "Défense", "Perf.Score", "Buts"]
    values = [
        player["rating"] / 10,
        player["pass_accuracy"] / 100,
        player["duels_won_pct"],
        min(player["defensive_impact"] / 30, 1),
        player["performance_score"],
        min(player["goals"] / 10, 1)
    ]

    N      = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    values += values[:1]

    fig, ax = plt.subplots(figsize=(7, 7),
                           subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    ax.plot(angles, values, color="#00d4aa", linewidth=2)
    ax.fill(angles, values, color="#00d4aa", alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, color="white", fontsize=11)
    ax.set_ylim(0, 1)
    ax.tick_params(colors="white")
    ax.spines["polar"].set_color("#333")
    ax.set_facecolor("#0d1117")
    ax.yaxis.set_tick_params(labelcolor="white")

    ax.set_title(f"🎯 Radar — {player_name}", color="white",
                 fontsize=14, fontweight="bold", pad=20)

    plt.tight_layout()
    plt.savefig(f"data/processed/chart_radar_{player_name.replace(' ', '_')}.png",
                dpi=150, bbox_inches="tight", facecolor="#0d1117")
    print(f"[SAUVEGARDÉ] chart_radar_{player_name}.png")
    plt.close()


# ─────────────────────────────────────────
# 7. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_charts():
    print("=" * 50)
    print("SMARTLINEUP — Génération des Graphiques")
    print("=" * 50)

    df_players, df_lineups, df_fixtures = load_data()

    chart_player_performance(df_players)
    chart_match_results(df_fixtures)
    chart_anomalies(df_players)
    chart_pass_network()
    chart_player_radar(df_players, "Vitinha")
    chart_player_radar(df_players, "Kylian Mbappé")

    print("\n" + "=" * 50)
    print("Graphiques générés dans data/processed/")
    print("=" * 50)


if __name__ == "__main__":
    run_charts()