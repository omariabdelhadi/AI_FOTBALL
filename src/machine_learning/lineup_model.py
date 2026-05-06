# src/machine_learning/lineup_model.py

import pandas as pd
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)
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
    print(f"[CHARGÉ] {len(df)} lignes, {len(df.columns)} colonnes")
    return df


# ─────────────────────────────────────────
# 2. PRÉPARER X ET Y
# ─────────────────────────────────────────

def prepare_xy(df):
    feature_cols = [
        "performance_score",
        "fatigue_index",
        "defensive_impact",
        "anomaly_z",
        "rating",
        "pass_accuracy",
        "duels_won_pct",
        "goals",
        "assists",
        "minutes",
        "appearances",
        "match_importance",
        "recent_form",
        "is_goalkeeper",
        "is_defender",
        "is_midfielder",
        "is_forward"
    ]

    X = df[feature_cols].fillna(0)
    y = df["is_starter"]

    print(f"[PRÊT] X={X.shape}, y={y.shape}")
    print(f"[PRÊT] Titulaires={y.sum()} | Remplaçants={(y==0).sum()}")
    return X, y, feature_cols


# ─────────────────────────────────────────
# 3. ENTRAÎNER LES MODÈLES
# ─────────────────────────────────────────

def train_models(X_train, y_train):
    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        ),
        "Logistic Regression": LogisticRegression(
            max_iter=1000,
            random_state=42
        )
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
        y_pred    = model.predict(X_test)
        acc_test  = accuracy_score(y_test, y_pred)
        acc_train = accuracy_score(y_train, model.predict(X_train))
        cv_scores = cross_val_score(model, X_train, y_train, cv=5)

        results[name] = {
            "accuracy_test":  round(acc_test, 4),
            "accuracy_train": round(acc_train, 4),
            "cv_mean":        round(cv_scores.mean(), 4),
            "cv_std":         round(cv_scores.std(), 4)
        }

        print(f"\n>>> {name}")
        print(f"    Accuracy Test  : {acc_test:.2%}")
        print(f"    Accuracy Train : {acc_train:.2%}")
        print(f"    CV Score       : {cv_scores.mean():.2%} ± {cv_scores.std():.2%}")
        print(f"\n    Rapport de classification :")
        print(classification_report(y_test, y_pred, target_names=["Remplaçant", "Titulaire"]))

    return results


# ─────────────────────────────────────────
# 5. MEILLEUR MODÈLE
# ─────────────────────────────────────────

def get_best_model(models, results):
    best_name = max(results, key=lambda k: results[k]["cv_mean"])
    best_model = models[best_name]
    print(f"\n[MEILLEUR MODÈLE] {best_name} → CV={results[best_name]['cv_mean']:.2%}")
    return best_name, best_model


# ─────────────────────────────────────────
# 6. IMPORTANCE DES FEATURES
# ─────────────────────────────────────────

def show_feature_importance(model, feature_cols, model_name):
    if not hasattr(model, "feature_importances_"):
        return

    importances = pd.Series(model.feature_importances_, index=feature_cols)
    importances = importances.sort_values(ascending=False)

    print(f"\n>>> Importance des features ({model_name}) :")
    for feat, score in importances.items():
        bar = "█" * int(score * 50)
        print(f"    {feat:<25} {score:.4f} {bar}")


# ─────────────────────────────────────────
# 7. PRÉDIRE LE LINEUP
# ─────────────────────────────────────────

def predict_lineup(model, scaler, df, feature_cols, fixture_id=None):
    """
    Prédit les 11 titulaires pour un match donné.
    Si fixture_id=None, utilise le dernier match disponible.
    """
    if fixture_id is None:
        fixture_id = df["fixture_id"].iloc[-1]

    df_match = df[df["fixture_id"] == fixture_id].copy()

    if df_match.empty:
        print(f"[ERREUR] Aucun joueur trouvé pour fixture_id={fixture_id}")
        return None

    X_match = df_match[feature_cols].fillna(0)
    X_match_scaled = scaler.transform(X_match)

    # Probabilité d'être titulaire
    proba = model.predict_proba(X_match_scaled)[:, 1]
    df_match["proba_starter"] = proba

    # Top 11
    df_match = df_match.sort_values("proba_starter", ascending=False)
    titulaires  = df_match.head(11)
    remplacants = df_match.tail(len(df_match) - 11)

    print(f"\n>>> Lineup prédit pour le match {fixture_id} :")
    print(f"\n{'Rang':<5} {'Joueur':<25} {'Position':<10} {'Proba':>6}")
    print("-" * 50)

    for i, (_, row) in enumerate(titulaires.iterrows(), 1):
        pos = row.get("position_match", row.get("position", "?"))
        print(f"  {i:<4} {row['player_name']:<25} {str(pos):<10} {row['proba_starter']:.2%}")

    return titulaires, remplacants


# ─────────────────────────────────────────
# 8. SAUVEGARDER LE MODÈLE
# ─────────────────────────────────────────

def save_model(model, scaler, model_name):
    os.makedirs("models", exist_ok=True)

    model_path  = "models/lineup_model.pkl"
    scaler_path = "models/scaler.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    print(f"\n[SAUVEGARDÉ] {model_path}")
    print(f"[SAUVEGARDÉ] {scaler_path}")


# ─────────────────────────────────────────
# 9. PIPELINE COMPLET
# ─────────────────────────────────────────

def run_lineup_model():
    print("=" * 50)
    print("SMARTLINEUP — Modèle Prédiction Titulaires")
    print("=" * 50)

    # Charger les données
    df = load_features()

    # Préparer X et y
    X, y, feature_cols = prepare_xy(df)

    # Normaliser
    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split train/test (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[SPLIT] Train={len(X_train)} | Test={len(X_test)}")

    # Entraîner les 3 modèles
    print("\n>>> Entraînement des modèles...")
    models = train_models(X_train, y_train)

    # Évaluer
    results = evaluate_models(models, X_train, X_test, y_train, y_test)

    # Meilleur modèle
    best_name, best_model = get_best_model(models, results)

    # Importance des features
    show_feature_importance(best_model, feature_cols, best_name)

    # Prédire le lineup du dernier match
    predict_lineup(best_model, scaler, df, feature_cols)

    # Sauvegarder
    save_model(best_model, scaler, best_name)

    print("\n" + "=" * 50)
    print("Modèle terminé !")
    print("=" * 50)

    return best_model, scaler


if __name__ == "__main__":
    run_lineup_model()