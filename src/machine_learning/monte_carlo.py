# src/machine_learning/monte_carlo.py

import pandas as pd
import numpy as np
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


# ─────────────────────────────────────────
# 1. CHARGER LES MATCHS DEPUIS MONGODB
# ─────────────────────────────────────────

def load_fixtures():
    client = MongoClient(MONGO_URI)
    db     = client["smartlineup"]
    df     = pd.DataFrame(list(db["fixtures"].find({}, {"_id": 0})))
    print(f"[CHARGÉ] {len(df)} matchs")
    return df


# ─────────────────────────────────────────
# 2. CALCULER LES PROBABILITÉS HISTORIQUES
# ─────────────────────────────────────────

def calculate_probabilities(df, team="Paris Saint-Germain"):
    """
    Calcule les probabilités W/D/L basées sur l'historique réel.
    """
    # Matchs à domicile
    home = df[df["home_team"] == team]
    # Matchs à l'extérieur
    away = df[df["away_team"] == team]

    total = len(df)
    if total == 0:
        return {"win": 0.33, "draw": 0.33, "loss": 0.34}

    wins  = len(df[df["result"] == "W"])
    draws = len(df[df["result"] == "D"])
    loses = len(df[df["result"] == "L"])

    prob_win  = wins  / total
    prob_draw = draws / total
    prob_loss = loses / total

    print(f"\n>>> Probabilités historiques du {team} :")
    print(f"    Victoires  : {wins}/{total}  → {prob_win:.2%}")
    print(f"    Nuls       : {draws}/{total} → {prob_draw:.2%}")
    print(f"    Défaites   : {loses}/{total} → {prob_loss:.2%}")

    return {
        "win":  prob_win,
        "draw": prob_draw,
        "loss": prob_loss
    }


# ─────────────────────────────────────────
# 3. SIMULATION MONTE CARLO
# ─────────────────────────────────────────

def simulate_match(prob_win, prob_draw, prob_loss, n_simulations=10000):
    """
    Simule n_simulations matchs basés sur les probabilités historiques.
    
    Chaque simulation tire un résultat aléatoire selon les probabilités :
    - prob_win  → victoire
    - prob_draw → nul
    - prob_loss → défaite
    """
    print(f"\n>>> Simulation de {n_simulations:,} matchs...")

    results = np.random.choice(
        ["W", "D", "L"],
        size=n_simulations,
        p=[prob_win, prob_draw, prob_loss]
    )

    wins  = np.sum(results == "W")
    draws = np.sum(results == "D")
    loses = np.sum(results == "L")

    prob_win_sim  = wins  / n_simulations
    prob_draw_sim = draws / n_simulations
    prob_loss_sim = loses / n_simulations

    return {
        "n_simulations": n_simulations,
        "wins":          int(wins),
        "draws":         int(draws),
        "losses":        int(loses),
        "prob_win":      round(prob_win_sim,  4),
        "prob_draw":     round(prob_draw_sim, 4),
        "prob_loss":     round(prob_loss_sim, 4)
    }


# ─────────────────────────────────────────
# 4. AFFICHER LES RÉSULTATS
# ─────────────────────────────────────────

def display_results(sim_results, team="Paris Saint-Germain", opponent="Adversaire"):
    n = sim_results["n_simulations"]

    print(f"\n{'=' * 50}")
    print(f"  {team} vs {opponent}")
    print(f"  Simulation Monte Carlo ({n:,} matchs)")
    print(f"{'=' * 50}")

    pw = sim_results["prob_win"]
    pd_ = sim_results["prob_draw"]
    pl = sim_results["prob_loss"]

    # Barre visuelle
    bar_w = "█" * int(pw  * 40)
    bar_d = "█" * int(pd_ * 40)
    bar_l = "█" * int(pl  * 40)

    print(f"\n  Victoire  {pw:.2%}  {bar_w}")
    print(f"  Nul       {pd_:.2%}  {bar_d}")
    print(f"  Défaite   {pl:.2%}  {bar_l}")

    print(f"\n  Sur {n:,} simulations :")
    print(f"    Victoires : {sim_results['wins']:,}")
    print(f"    Nuls      : {sim_results['draws']:,}")
    print(f"    Défaites  : {sim_results['losses']:,}")

    # Verdict
    print(f"\n  Verdict : ", end="")
    if pw >= pd_ and pw >= pl:
        print(f"✅ {team} favori ({pw:.2%} de chances de gagner)")
    elif pd_ >= pw and pd_ >= pl:
        print(f"⚖️  Match nul probable ({pd_:.2%})")
    else:
        print(f"⚠️  {opponent} favori ({pl:.2%} de chances de gagner)")

    print(f"{'=' * 50}")


# ─────────────────────────────────────────
# 5. SIMULATION AVEC FACTEUR ADVERSAIRE
# ─────────────────────────────────────────

def simulate_with_opponent(base_probs, opponent_strength=0.5, home=True):
    """
    Ajuste les probabilités selon la force de l'adversaire.
    
    opponent_strength : entre 0 (faible) et 1 (très fort)
    home : True si PSG joue à domicile
    """
    pw = base_probs["win"]
    pd_ = base_probs["draw"]
    pl = base_probs["loss"]

    # Avantage domicile +5%
    home_bonus = 0.05 if home else -0.05

    # Pénalité selon force adversaire
    opponent_penalty = opponent_strength * 0.2

    pw_adj  = max(0, pw  + home_bonus - opponent_penalty)
    pl_adj  = min(1, pl  - home_bonus + opponent_penalty)
    pd_adj  = max(0, 1 - pw_adj - pl_adj)

    # Normaliser pour que la somme = 1
    total   = pw_adj + pd_adj + pl_adj
    pw_adj  = pw_adj  / total
    pd_adj  = pd_adj  / total
    pl_adj  = pl_adj  / total

    print(f"\n>>> Ajustement selon adversaire (force={opponent_strength}, domicile={home}) :")
    print(f"    Victoire ajustée : {pw_adj:.2%}")
    print(f"    Nul ajusté       : {pd_adj:.2%}")
    print(f"    Défaite ajustée  : {pl_adj:.2%}")

    return {
        "win":  pw_adj,
        "draw": pd_adj,
        "loss": pl_adj
    }


# ─────────────────────────────────────────
# 6. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_monte_carlo(team="Paris Saint-Germain", opponent="Olympique de Marseille",
                    opponent_strength=0.7, home=True, n_simulations=10000):

    print("=" * 50)
    print("SMARTLINEUP — Simulation Monte Carlo")
    print("=" * 50)

    # Charger les matchs
    df = load_fixtures()

    # Probabilités historiques
    base_probs = calculate_probabilities(df, team)

    # Ajuster selon l'adversaire
    adj_probs = simulate_with_opponent(base_probs, opponent_strength, home)

    # Simuler
    sim_results = simulate_match(
        adj_probs["win"],
        adj_probs["draw"],
        adj_probs["loss"],
        n_simulations
    )

    # Afficher
    display_results(sim_results, team, opponent)

    # Sauvegarder
    os.makedirs("data/processed", exist_ok=True)
    pd.DataFrame([sim_results]).to_csv(
        "data/processed/monte_carlo_results.csv", index=False
    )
    print(f"\n[SAUVEGARDÉ] data/processed/monte_carlo_results.csv")

    return sim_results


if __name__ == "__main__":
    run_monte_carlo(
        team              = "Paris Saint-Germain",
        opponent          = "Olympique de Marseille",
        opponent_strength = 0.7,   # 0=faible 1=très fort
        home              = True,  # PSG à domicile
        n_simulations     = 10000
    )
