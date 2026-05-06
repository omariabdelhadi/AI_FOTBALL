# src/machine_learning/performance_model.py

import pandas as pd
import numpy as np
import os
import pickle
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────
# 1. CHARGER LES FEATURES
# ─────────────────────────────────────────

def load_features():
    path = "data/processed/features.csv"
    if not os.path.exists(path):
        raise FileNotFoundError("Lance d'abord features.py !")

    df = pd.read_csv(path)
    print(f"[CHARGÉ] {len(df)} lignes")
    return df


# ─────────────────────────────────────────
# 2. PRÉPARER X ET Y
# ─────────────────────────────────────────

def prepare_xy(df):
    """
    X = features du joueur
    y = rating (la performance réelle du joueur)
    On prédit le rating futur d'un joueur.
    """
    feature_cols = [
        "goals",
        "assists",
        "minutes",
        "appearances",
        "pass_accuracy",
        "duels_won_pct",
        "defensive_impact",
        "fatigue_index",
        "match_importance",
        "recent_form",
        "is_goalkeeper",
        "is_defender",
        "is_midfielder",
        "is_forward"
    ]

    # Garder seulement les joueurs avec un rating réel
    df = df[df["rating"] > 0].copy()

    X = df[feature_cols].fillna(0)
    y = df["rating"]

    print(f"[PRÊT] X={X.shape} | y min={y.min():.2f} max={y.max():.2f} moy={y.mean():.2f}")
    return X, y, feature_cols, df


# ─────────────────────────────────────────
# 3. ENTRAÎNER LES MODÈLES
# ─────────────────────────────────────────

def train_models(X_train, y_train):
    models = {
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42
        ),
        "Random Forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        ),
        "Linear Regression": LinearRegression()
    }

    trained = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        trained[name] = model
        print(f"[ENTRAÎNÉ] {name}")

    return trained


# ─────────────────────────────────────────
# 4. ÉVALUER LES MODÈLES
# ─────────────────────────────────────────

def evaluate_models(models, X_train, X_test, y_train, y_test):
    print("\n" + "=" * 50)
    print("ÉVALUATION DES MODÈLES")
    print("=" * 50)

    results = {}

    for name, model in models.items():
        y_pred = model.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        r2  = r2_score(y_test, y_pred)
        cv  = cross_val_score(model, X_train, y_train, cv=5, scoring="r2")

        results[name] = {
            "mae":    round(mae, 4),
            "r2":     round(r2, 4),
            "cv_r2":  round(cv.mean(), 4)
        }

        print(f"\n>>> {name}")
        print(f"    MAE (erreur moyenne) : {mae:.4f}")
        print(f"    R² Score             : {r2:.4f}")
        print(f"    CV R²                : {cv.mean():.4f} ± {cv.std():.4f}")

        # Afficher quelques prédictions vs réalité
        print(f"\n    Exemples prédictions vs réalité :")
        print(f"    {'Réel':>8} {'Prédit':>8} {'Écart':>8}")
        for real, pred in zip(list(y_test[:5]), list(y_pred[:5])):
            ecart = pred - real
            print(f"    {real:>8.3f} {pred:>8.3f} {ecart:>+8.3f}")

    return results


# ─────────────────────────────────────────
# 5. MEILLEUR MODÈLE
# ─────────────────────────────────────────

def get_best_model(models, results):
    best_name  = max(results, key=lambda k: results[k]["r2"])
    best_model = models[best_name]
    print(f"\n[MEILLEUR MODÈLE] {best_name} → R²={results[best_name]['r2']:.4f}")
    return best_name, best_model


# ─────────────────────────────────────────
# 6. PRÉDIRE LA PERFORMANCE D'UN JOUEUR
# ─────────────────────────────────────────

def predict_player_performance(model, scaler, df, feature_cols, player_name):
    """
    Prédit le rating futur d'un joueur spécifique.
    """
    df_player = df[df["player_name"] == player_name]

    if df_player.empty:
        print(f"[ERREUR] Joueur '{player_name}' introuvable.")
        return None

    X_player = df_player[feature_cols].fillna(0)
    X_scaled  = scaler.transform(X_player)
    predicted = model.predict(X_scaled)

    real_rating = df_player["rating"].values[0]
    pred_rating = predicted[0]

    print(f"\n>>> Prédiction de performance : {player_name}")
    print(f"    Rating réel    : {real_rating:.3f}")
    print(f"    Rating prédit  : {pred_rating:.3f}")
    print(f"    Écart          : {pred_rating - real_rating:+.3f}")

    if pred_rating >= real_rating:
        print(f"    Tendance       : 📈 En progression")
    else:
        print(f"    Tendance       : 📉 En baisse")

    return pred_rating


# ─────────────────────────────────────────
# 7. PRÉDIRE TOUS LES JOUEURS
# ─────────────────────────────────────────

def predict_all_players(model, scaler, df, feature_cols):
    """
    Prédit le rating de tous les joueurs et les classe.
    """
    df = df.copy()
    X  = df[feature_cols].fillna(0)
    X_scaled = scaler.transform(X)

    df["predicted_rating"] = model.predict(X_scaled)
    df["ecart"]            = df["predicted_rating"] - df["rating"]

    # Classement par rating prédit
    df_sorted = df[["player_name", "rating", "predicted_rating", "ecart"]]\
        .drop_duplicates(subset="player_name")\
        .sort_values("predicted_rating", ascending=False)\
        .reset_index(drop=True)

    print(f"\n>>> Classement des joueurs par performance prédite :")
    print(f"\n{'Rang':<5} {'Joueur':<25} {'Rating Réel':>12} {'Rating Prédit':>14} {'Écart':>8}")
    print("-" * 68)

    for i, row in df_sorted.head(15).iterrows():
        tendance = "📈" if row["ecart"] >= 0 else "📉"
        print(f"  {i+1:<4} {row['player_name']:<25} {row['rating']:>12.3f} {row['predicted_rating']:>14.3f} {row['ecart']:>+7.3f} {tendance}")

    return df_sorted


# ─────────────────────────────────────────
# 8. SAUVEGARDER
# ─────────────────────────────────────────

def save_model(model, scaler):
    os.makedirs("models", exist_ok=True)

    with open("models/performance_model.pkl", "wb") as f:
        pickle.dump(model, f)

    with open("models/performance_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    print(f"\n[SAUVEGARDÉ] models/performance_model.pkl")
    print(f"[SAUVEGARDÉ] models/performance_scaler.pkl")


# ─────────────────────────────────────────
# 9. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_performance_model():
    print("=" * 50)
    print("SMARTLINEUP — Modèle Prédiction Performance")
    print("=" * 50)

    # Charger
    df = load_features()

    # Préparer X et y
    X, y, feature_cols, df_clean = prepare_xy(df)

    # Normaliser
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )
    print(f"[SPLIT] Train={len(X_train)} | Test={len(X_test)}")

    # Entraîner
    print("\n>>> Entraînement des modèles...")
    models = train_models(X_train, y_train)

    # Évaluer
    results = evaluate_models(models, X_train, X_test, y_train, y_test)

    # Meilleur modèle
    best_name, best_model = get_best_model(models, results)

    # Prédire tous les joueurs
    predict_all_players(best_model, scaler, df_clean, feature_cols)

    # Prédire un joueur spécifique
    predict_player_performance(best_model, scaler, df_clean, feature_cols, "Vitinha")

    # Sauvegarder
    save_model(best_model, scaler)

    print("\n" + "=" * 50)
    print("Modèle Performance terminé !")
    print("=" * 50)

    return best_model, scaler


if __name__ == "__main__":
    run_performance_model()