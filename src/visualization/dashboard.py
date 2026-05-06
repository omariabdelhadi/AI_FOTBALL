# src/visualization/dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Ajouter le chemin src
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.machine_learning.monte_carlo import simulate_match, simulate_with_opponent
from src.machine_learning.anomaly import detect_anomalies
from src.analytics.tactical import calculate_tactical_fit, FORMATIONS, build_optimal_lineup
from src.analytics.transfer import prepare_similarity_features, calculate_similarity, find_similar_players

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

st.set_page_config(
    page_title="SmartLineup",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: #1a1a2e;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #00d4aa;
    }
    [data-testid="stMetricLabel"] { color: #00d4aa !important; }
    [data-testid="stMetricValue"] { color: white !important; }
    h1, h2, h3 { color: #00d4aa; }
    .stButton>button {
        background-color: #00d4aa;
        color: black;
        font-weight: bold;
        border-radius: 8px;
        width: 100%;
    }
    .stButton>button:hover { background-color: #00b894; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────

@st.cache_data
def load_all_data():
    client      = MongoClient(MONGO_URI)
    db          = client["smartlineup"]
    df_players  = pd.DataFrame(list(db["players"].find({}, {"_id": 0})))
    df_lineups  = pd.DataFrame(list(db["lineups"].find({}, {"_id": 0})))
    df_fixtures = pd.DataFrame(list(db["fixtures"].find({}, {"_id": 0})))
    return df_players, df_lineups, df_fixtures


@st.cache_resource
def load_models():
    models = {}
    paths  = {
        "lineup":             "models/lineup_model.pkl",
        "scaler":             "models/scaler.pkl",
        "performance":        "models/performance_model.pkl",
        "performance_scaler": "models/performance_scaler.pkl"
    }
    for name, path in paths.items():
        if os.path.exists(path):
            with open(path, "rb") as f:
                models[name] = pickle.load(f)
    return models


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

def render_sidebar():
    st.sidebar.title("⚽ SmartLineup")
    st.sidebar.markdown("---")

    page = st.sidebar.radio("Navigation", [
        "🏠 Accueil",
        "👥 Lineup Prédit",
        "📈 Performance",
        "🎯 Simulation Match",
        "🔍 Anomalies",
        "🗺️ Réseau de Passes",
        "💼 Transferts",
        "⚙️ Tactique"
    ])

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Saison :** 2022/2023")
    st.sidebar.markdown("**Ligues :** Premier League, Ligue 1, Bundesliga, Serie A, La Liga")

    return page


# ─────────────────────────────────────────
# PAGE : ACCUEIL
# ─────────────────────────────────────────

def page_accueil(df_players, df_fixtures):
    st.title("⚽ SmartLineup — Tableau de Bord")
    st.markdown("Système intelligent de prédiction des performances et compositions")
    st.markdown("---")

    df_clean = df_players[df_players["rating"] > 0]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Joueurs", len(df_players))
    with col2:
        st.metric("🏟️ Équipes", df_players["team"].nunique())
    with col3:
        st.metric("🌍 Ligues", df_players["league"].nunique())
    with col4:
        avg = df_clean["rating"].mean()
        st.metric("⭐ Rating Moyen", f"{avg:.2f}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Joueurs par Ligue")
        counts = df_players["league"].value_counts()
        st.bar_chart(counts)

    with col2:
        st.subheader("⭐ Top 10 Joueurs")
        leagues = ["Toutes"] + sorted(df_clean["league"].unique().tolist())
        selected_league = st.selectbox("Ligue :", leagues)

        if selected_league != "Toutes":
            df_filtered = df_clean[df_clean["league"] == selected_league]
        else:
            df_filtered = df_clean

        top = df_filtered.nlargest(10, "rating")[
            ["player_name", "team", "league", "rating", "position", "goals", "assists"]
        ].reset_index(drop=True)
        top.index += 1
        st.dataframe(top, use_container_width=True)


# ─────────────────────────────────────────
# PAGE : LINEUP PRÉDIT
# ─────────────────────────────────────────

def page_lineup(df_players, models):
    st.title("👥 Lineup Prédit")
    st.markdown("Prédiction des 11 titulaires basée sur le Machine Learning")
    st.markdown("---")

    if "lineup" not in models:
        st.error("Modèle lineup introuvable. Lance d'abord lineup_model.py")
        return

    feature_cols = [
        "performance_score", "fatigue_index", "defensive_impact",
        "anomaly_z", "rating", "pass_accuracy", "duels_won_pct",
        "goals", "assists", "minutes", "appearances",
        "match_importance", "recent_form",
        "is_goalkeeper", "is_defender", "is_midfielder", "is_forward"
    ]

    # Choisir une ligue puis une équipe
    leagues = sorted(df_players["league"].unique().tolist())
    selected_league = st.selectbox("Choisir une ligue :", leagues)

    df_league = df_players[df_players["league"] == selected_league]
    teams     = sorted(df_league["team"].unique().tolist())
    selected_team = st.selectbox("Choisir une équipe :", teams)

    df_team = df_players[df_players["team"] == selected_team].copy()

    if df_team.empty:
        st.warning("Aucun joueur trouvé.")
        return

    # Préparer les features
    for col in ["match_importance", "recent_form",
                "is_goalkeeper", "is_defender", "is_midfielder", "is_forward"]:
        if col not in df_team.columns:
            df_team[col] = 0

    df_team["is_goalkeeper"] = (df_team["position"] == "Goalkeeper").astype(int)
    df_team["is_defender"]   = (df_team["position"] == "Defender").astype(int)
    df_team["is_midfielder"] = (df_team["position"] == "Midfielder").astype(int)
    df_team["is_forward"]    = (df_team["position"].isin(["Forward", "Attacker"])).astype(int)
    df_team["match_importance"] = 0.5
    df_team["recent_form"]      = 0.5

    X        = df_team[feature_cols].fillna(0)
    X_scaled = models["scaler"].transform(X)
    proba    = models["lineup"].predict_proba(X_scaled)[:, 1]

    df_team["proba_starter"] = proba
    df_team = df_team.sort_values("proba_starter", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("✅ 11 Titulaires Prédits")
        titulaires = df_team.head(11)[
            ["player_name", "position", "rating", "proba_starter"]
        ].reset_index(drop=True)
        titulaires.index += 1
        titulaires["proba_starter"] = titulaires["proba_starter"].apply(
            lambda x: f"{x:.2%}"
        )
        st.dataframe(titulaires, use_container_width=True)

    with col2:
        st.subheader("🔄 Remplaçants")
        remplacants = df_team.iloc[11:][
            ["player_name", "position", "rating", "proba_starter"]
        ].reset_index(drop=True)
        remplacants.index += 1
        remplacants["proba_starter"] = remplacants["proba_starter"].apply(
            lambda x: f"{x:.2%}"
        )
        st.dataframe(remplacants, use_container_width=True)


# ─────────────────────────────────────────
# PAGE : PERFORMANCE
# ─────────────────────────────────────────

def page_performance(df_players, models):
    st.title("📈 Prédiction de Performance")
    st.markdown("Estimation du rating futur de chaque joueur")
    st.markdown("---")

    df_clean = df_players[df_players["rating"] > 0].copy()

    feature_cols = [
        "goals", "assists", "minutes", "appearances",
        "pass_accuracy", "duels_won_pct", "defensive_impact",
        "fatigue_index", "match_importance", "recent_form",
        "is_goalkeeper", "is_defender", "is_midfielder", "is_forward"
    ]

    for col in ["match_importance", "recent_form",
                "is_goalkeeper", "is_defender", "is_midfielder", "is_forward"]:
        if col not in df_clean.columns:
            df_clean[col] = 0

    df_clean["is_goalkeeper"] = (df_clean["position"] == "Goalkeeper").astype(int)
    df_clean["is_defender"]   = (df_clean["position"] == "Defender").astype(int)
    df_clean["is_midfielder"] = (df_clean["position"] == "Midfielder").astype(int)
    df_clean["is_forward"]    = (df_clean["position"].isin(["Forward", "Attacker"])).astype(int)

    # Filtrer par ligue puis équipe puis joueur
    leagues = ["Toutes"] + sorted(df_clean["league"].unique().tolist())
    selected_league = st.selectbox("Ligue :", leagues)

    if selected_league != "Toutes":
        df_clean = df_clean[df_clean["league"] == selected_league]

    teams = ["Toutes"] + sorted(df_clean["team"].unique().tolist())
    selected_team = st.selectbox("Équipe :", teams)

    if selected_team != "Toutes":
        df_clean = df_clean[df_clean["team"] == selected_team]

    players  = df_clean["player_name"].tolist()
    selected = st.selectbox("Choisir un joueur :", players)

    player_row = df_clean[df_clean["player_name"] == selected].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rating Actuel", f"{player_row['rating']:.3f}")
    with col2:
        st.metric("Buts", int(player_row["goals"]))
    with col3:
        st.metric("Passes Décisives", int(player_row["assists"]))

    if "performance" in models and "performance_scaler" in models:
        X         = df_clean[df_clean["player_name"] == selected][feature_cols].fillna(0)
        X_scaled  = models["performance_scaler"].transform(X)
        predicted = models["performance"].predict(X_scaled)[0]

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rating Prédit", f"{predicted:.3f}")
        with col2:
            ecart = predicted - player_row["rating"]
            st.metric("Écart", f"{ecart:+.3f}")
        with col3:
            tendance = "📈 En progression" if predicted >= player_row["rating"] \
                       else "📉 En baisse"
            st.metric("Tendance", tendance)

    st.markdown("---")
    st.subheader("📊 Stats Complètes")
    stats = player_row[[
        "rating", "goals", "assists", "minutes",
        "pass_accuracy", "duels_won_pct", "defensive_impact",
        "performance_score", "fatigue_index"
    ]].to_frame("Valeur")
    st.dataframe(stats, use_container_width=True)


# ─────────────────────────────────────────
# PAGE : SIMULATION MATCH (MONTE CARLO)
# ─────────────────────────────────────────

def page_simulation(df_players, df_fixtures):
    st.title("🎯 Simulation Monte Carlo")
    st.markdown("Simulez le résultat d'un match en 10 000 simulations")
    st.markdown("---")

    # Toutes les équipes depuis Kaggle
    all_teams = sorted(df_players["team"].unique().tolist())

    col1, col2 = st.columns(2)

    with col1:
        team = st.selectbox("🏠 Équipe :", all_teams)
        home = st.toggle("Joue à domicile", value=True)

    with col2:
        opponent = st.selectbox("⚔️ Adversaire :", all_teams)
        strength = st.slider("Force de l'adversaire", 0.0, 1.0, 0.5, 0.1)

    n_sims = st.select_slider(
        "Nombre de simulations",
        options=[1000, 5000, 10000, 50000],
        value=10000
    )

    if st.button("🚀 Lancer la Simulation"):
        total = len(df_fixtures)
        wins  = len(df_fixtures[df_fixtures["result"] == "W"])
        draws = len(df_fixtures[df_fixtures["result"] == "D"])
        loses = len(df_fixtures[df_fixtures["result"] == "L"])

        base_probs = {
            "win":  wins  / total,
            "draw": draws / total,
            "loss": loses / total
        }

        adj     = simulate_with_opponent(base_probs, strength, home)
        results = simulate_match(adj["win"], adj["draw"], adj["loss"], n_sims)

        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("✅ Victoire",
                      f"{results['prob_win']:.2%}",
                      f"{results['wins']:,} fois")
        with col2:
            st.metric("⚖️ Nul",
                      f"{results['prob_draw']:.2%}",
                      f"{results['draws']:,} fois")
        with col3:
            st.metric("❌ Défaite",
                      f"{results['prob_loss']:.2%}",
                      f"{results['losses']:,} fois")

        st.markdown("---")
        if results["prob_win"] >= results["prob_loss"]:
            st.success(f"✅ **{team}** est favori avec "
                      f"**{results['prob_win']:.2%}** de chances de gagner !")
        else:
            st.warning(f"⚠️ **{opponent}** est favori avec "
                      f"**{results['prob_loss']:.2%}** de chances de gagner !")

        df_chart = pd.DataFrame({
            "Résultat":    ["Victoire", "Nul", "Défaite"],
            "Probabilité": [results["prob_win"],
                            results["prob_draw"],
                            results["prob_loss"]]
        })
        st.bar_chart(df_chart.set_index("Résultat"))


# ─────────────────────────────────────────
# PAGE : ANOMALIES
# ─────────────────────────────────────────

def page_anomalies(df_players):
    st.title("🔍 Détection d'Anomalies")
    st.markdown("Joueurs qui sur/sous-performent par rapport à la moyenne")
    st.markdown("---")

    df_clean = df_players[df_players["rating"] > 0].copy()

    # Filtrer par ligue
    leagues = ["Toutes"] + sorted(df_clean["league"].unique().tolist())
    selected_league = st.selectbox("Ligue :", leagues)

    if selected_league != "Toutes":
        df_clean = df_clean[df_clean["league"] == selected_league]

    # Filtrer par équipe
    teams = ["Toutes"] + sorted(df_clean["team"].unique().tolist())
    selected_team = st.selectbox("Équipe :", teams)

    if selected_team != "Toutes":
        df_clean = df_clean[df_clean["team"] == selected_team]

    df_clean = detect_anomalies(df_clean)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ Normaux",
                  len(df_clean[df_clean["anomaly_type"] == "Normal"]))
    with col2:
        st.metric("🌟 Surperformance",
                  len(df_clean[df_clean["anomaly_type"] == "Surperformance"]))
    with col3:
        st.metric("⚠️ Sous-performance",
                  len(df_clean[df_clean["anomaly_type"] == "Sous-performance"]))
    with col4:
        st.metric("👀 Attention",
                  len(df_clean[df_clean["anomaly_type"] == "Attention"]))

    st.markdown("---")

    filtre = st.selectbox("Filtrer par type :", [
        "Tous", "Surperformance", "Sous-performance", "Attention", "Normal"
    ])

    df_show = df_clean if filtre == "Tous" else \
              df_clean[df_clean["anomaly_type"] == filtre]

    df_show = df_show[[
        "player_name", "team", "league", "position", "rating",
        "performance_score", "anomaly_score", "anomaly_type"
    ]].sort_values("anomaly_score", ascending=False).reset_index(drop=True)
    df_show.index += 1

    st.dataframe(df_show, use_container_width=True)


# ─────────────────────────────────────────
# PAGE : RÉSEAU DE PASSES
# ─────────────────────────────────────────

def page_pass_network(df_players):
    st.title("🗺️ Réseau de Passes")
    st.markdown("Visualisation des connexions entre joueurs")
    st.markdown("---")

    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use("Agg")

    # Choisir ligue et équipe
    leagues = sorted(df_players["league"].unique().tolist())
    selected_league = st.selectbox("Choisir une ligue :", leagues)
    df_league = df_players[df_players["league"] == selected_league]

    teams = sorted(df_league["team"].unique().tolist())
    selected_team = st.selectbox("Choisir une équipe :", teams)

    df_team = df_players[
        (df_players["team"] == selected_team) &
        (df_players["rating"] > 0)
    ].copy()

    if df_team.empty:
        st.warning("Aucun joueur trouvé.")
        return

    # Prendre top 11 joueurs par minutes joués
    df_team = df_team.nlargest(11, "minutes").reset_index(drop=True)

    # Position Y sur le terrain
    pos_y = {
        "Goalkeeper": 0.08,
        "Defender":   0.28,
        "Midfielder": 0.58,
        "Forward":    0.82,
        "Attacker":   0.82
    }

    # Grouper par position
    pos_groups = {}
    for _, row in df_team.iterrows():
        pos = row["position"]
        if pos not in pos_groups:
            pos_groups[pos] = []
        pos_groups[pos].append(row["player_name"])

    # Calculer coordonnées
    coords = {}
    for pos, players in pos_groups.items():
        n  = len(players)
        y  = pos_y.get(pos, 0.5)
        xs = np.linspace(0.15, 0.85, n)
        for i, player in enumerate(players):
            coords[player] = (xs[i], y)

    # Construire les arêtes
    position_order = {
        "Goalkeeper": 0, "Defender": 1,
        "Midfielder": 2, "Forward": 3, "Attacker": 3
    }

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
                w = (p1["passes_total"] + p2["passes_total"]) / 2
                edges.append({"from": p1["player_name"],
                              "to":   p2["player_name"],
                              "weight": w})

    # Dessiner
    fig, ax = plt.subplots(figsize=(9, 12))
    fig.patch.set_facecolor("#1a6b1a")
    ax.set_facecolor("#1a6b1a")

    ax.add_patch(plt.Rectangle((0.05, 0.02), 0.9, 0.96,
                 fill=False, edgecolor="white", linewidth=2))
    ax.axhline(y=0.5, color="white", linewidth=1.5, alpha=0.5)
    ax.add_patch(plt.Circle((0.5, 0.5), 0.1,
                 fill=False, edgecolor="white", linewidth=1.5, alpha=0.5))

    # Top 12 arêtes
    edges_sorted = sorted(edges, key=lambda x: x["weight"], reverse=True)[:12]
    max_w = edges_sorted[0]["weight"] if edges_sorted else 1

    for edge in edges_sorted:
        if edge["from"] in coords and edge["to"] in coords:
            x1, y1 = coords[edge["from"]]
            x2, y2 = coords[edge["to"]]
            alpha  = edge["weight"] / max_w * 0.7
            lw     = edge["weight"] / max_w * 4
            ax.plot([x1, x2], [y1, y2],
                    color="#00d4aa", alpha=alpha, linewidth=lw)

    # Nœuds
    for _, row in df_team.iterrows():
        if row["player_name"] not in coords:
            continue
        x, y = coords[row["player_name"]]
        size = 400 + row["passes_total"] * 0.05
        ax.scatter(x, y, s=size, color="#00d4aa",
                   zorder=5, edgecolors="white", linewidth=2)
        name = row["player_name"].split()[-1]
        ax.text(x, y - 0.05, name, ha="center",
                color="white", fontsize=9, fontweight="bold")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(f"🔗 Réseau de Passes — {selected_team}",
                 color="white", fontsize=14, fontweight="bold", pad=15)

    st.pyplot(fig)
    plt.close()

    # Centralité
    st.markdown("---")
    st.subheader("📊 Centralité des Joueurs")
    centrality = {}
    for edge in edges:
        centrality[edge["from"]] = centrality.get(edge["from"], 0) + edge["weight"]
        centrality[edge["to"]]   = centrality.get(edge["to"],   0) + edge["weight"]

    df_centrality = pd.DataFrame({
        "Joueur":     list(centrality.keys()),
        "Centralité": list(centrality.values())
    }).sort_values("Centralité", ascending=False).reset_index(drop=True)
    df_centrality.index += 1

    st.dataframe(df_centrality, use_container_width=True)
    # Exclure le gardien du joueur clé
    df_no_gk = df_team[df_team["position"] != "Goalkeeper"]
    if not df_no_gk.empty:
        key_player = df_centrality[
            ~df_centrality["Joueur"].isin(
                df_team[df_team["position"] == "Goalkeeper"]["player_name"].values
            )
        ].iloc[0]["Joueur"]
        st.success(f"⭐ Joueur clé : **{key_player}**")


# ─────────────────────────────────────────
# PAGE : TRANSFERTS
# ─────────────────────────────────────────

def page_transferts(df_players):
    st.title("💼 Recommandation de Transferts")
    st.markdown("Trouvez les joueurs similaires et les meilleures recrues")
    st.markdown("---")

    df_clean, X_scaled, _ = prepare_similarity_features(df_players)
    similarity_matrix     = calculate_similarity(X_scaled)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔁 Joueurs Similaires")

        leagues  = ["Toutes"] + sorted(df_clean["league"].unique().tolist())
        sel_lg   = st.selectbox("Ligue :", leagues, key="transfer_league")
        df_filt  = df_clean if sel_lg == "Toutes" else \
                   df_clean[df_clean["league"] == sel_lg]

        players  = df_filt["player_name"].tolist()
        selected = st.selectbox("Choisir un joueur :", players)

        if st.button("🔍 Trouver similaires"):
            similar = find_similar_players(
                df_clean, similarity_matrix, selected, top_n=5
            )
            if similar:
                st.dataframe(pd.DataFrame(similar), use_container_width=True)

    with col2:
        st.subheader("🎯 Recommandations Recrutement")
        league_filter = st.selectbox("Ligue cible :", leagues, key="rec_league")
        position      = st.selectbox("Position :", [
            "Toutes", "Goalkeeper", "Defender", "Midfielder", "Forward"
        ])
        min_rating = st.slider("Rating minimum :", 6.0, 10.0, 7.0, 0.1)
        budget     = st.slider("Budget (M€) :", 10, 200, 50, 10)

        if st.button("💼 Recommander"):
            df_rec = df_clean.copy()
            df_rec["estimated_value"] = (
                df_rec["rating"] * df_rec["minutes"] * 0.001
            ).round(2)

            if league_filter != "Toutes":
                df_rec = df_rec[df_rec["league"] == league_filter]
            if position != "Toutes":
                df_rec = df_rec[df_rec["position"] == position]

            df_rec = df_rec[
                (df_rec["rating"] >= min_rating) &
                (df_rec["estimated_value"] <= budget)
            ].sort_values("rating", ascending=False)

            if df_rec.empty:
                st.warning("Aucun joueur trouvé avec ces critères.")
            else:
                st.dataframe(
                    df_rec[["player_name", "team", "league",
                             "position", "rating", "estimated_value"]]
                    .head(10).reset_index(drop=True),
                    use_container_width=True
                )


# ─────────────────────────────────────────
# PAGE : TACTIQUE
# ─────────────────────────────────────────

def page_tactique(df_players):
    st.title("⚙️ Analyse Tactique")
    st.markdown("Trouvez la meilleure formation pour votre équipe")
    st.markdown("---")

    df_clean = df_players[df_players["rating"] > 0].copy()

    # Filtrer par ligue puis équipe
    leagues = sorted(df_clean["league"].unique().tolist())
    selected_league = st.selectbox("Choisir une ligue :", leagues)
    df_clean = df_clean[df_clean["league"] == selected_league]

    teams = sorted(df_clean["team"].unique().tolist())
    selected_team = st.selectbox("Choisir une équipe :", teams)
    df_clean = df_clean[df_clean["team"] == selected_team].copy()

    # Choisir une formation
    formation = st.selectbox("Choisir une formation :", list(FORMATIONS.keys()))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"🏆 TacticalFit — {formation}")
        df_fit = calculate_tactical_fit(df_clean, formation)
        if df_fit is not None:
            df_fit = df_fit.sort_values("tactical_fit", ascending=False)
            st.dataframe(
                df_fit[["player_name", "position", "rating", "tactical_fit"]]
                .reset_index(drop=True),
                use_container_width=True
            )

    with col2:
        st.subheader(f"✅ Lineup Optimal — {formation}")
        df_lineup = build_optimal_lineup(df_clean, formation)
        if df_lineup is not None:
            st.dataframe(
                df_lineup[["player_name", "position", "rating"]]
                .reset_index(drop=True),
                use_container_width=True
            )

    st.markdown("---")
    st.subheader("📊 Comparaison des Formations")

    scores = {}
    for f in FORMATIONS:
        df_f = calculate_tactical_fit(df_clean, f)
        if df_f is not None:
            scores[f] = round(df_f["tactical_fit"].mean(), 4)

    df_scores = pd.DataFrame({
        "Formation":   list(scores.keys()),
        "TacticalFit": list(scores.values())
    }).sort_values("TacticalFit", ascending=False).reset_index(drop=True)
    df_scores.index += 1

    st.dataframe(df_scores, use_container_width=True)
    st.bar_chart(df_scores.set_index("Formation"))


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    df_players, df_lineups, df_fixtures = load_all_data()
    models = load_models()
    page   = render_sidebar()

    if page == "🏠 Accueil":
        page_accueil(df_players, df_fixtures)
    elif page == "👥 Lineup Prédit":
        page_lineup(df_players, models)
    elif page == "📈 Performance":
        page_performance(df_players, models)
    elif page == "🎯 Simulation Match":
        page_simulation(df_players, df_fixtures)
    elif page == "🔍 Anomalies":
        page_anomalies(df_players)
    elif page == "🗺️ Réseau de Passes":
        page_pass_network(df_players)
    elif page == "💼 Transferts":
        page_transferts(df_players)
    elif page == "⚙️ Tactique":
        page_tactique(df_players)


if __name__ == "__main__":
    main()