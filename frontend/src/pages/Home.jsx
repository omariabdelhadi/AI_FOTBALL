// frontend/src/pages/Home.jsx

import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import './Home.css';

const features = [
  { icon: "⚡", title: "Lineup Prédit",   desc: "Prédit les 11 titulaires via Machine Learning" },
  { icon: "📊", title: "Performance",     desc: "Estime le rating futur d'un joueur" },
  { icon: "🎲", title: "Simulation",      desc: "Monte Carlo sur 10 000 matchs simulés" },
  { icon: "📡", title: "Anomalies",       desc: "Détecte les joueurs qui sur/sous-performent" },
  { icon: "🔄", title: "Transferts",      desc: "Recommande les meilleures recrues par budget" },
  { icon: "🧩", title: "Tactique",        desc: "Analyse la meilleure formation pour l'équipe" },
];

const stats = [
  { value: "2689", label: "Joueurs" },
  { value: "98",   label: "Équipes" },
  { value: "5",    label: "Ligues" },
  { value: "3",    label: "Modèles ML" },
];

function Home() {
  const [leagues, setLeagues] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getLeagues()
      .then(data => {
        setLeagues(data.leagues || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div>
      {/* Hero */}
      <div className="home-hero">
        <h1 className="home-hero-title">
          Smart<span>Lineup</span>
        </h1>
        <p className="home-hero-subtitle">
          Système intelligent de prédiction des performances
          et compositions en football — propulsé par le Machine Learning
        </p>
      </div>

      {/* Stats */}
      <div className="home-stats">
        {stats.map(s => (
          <div key={s.label} className="home-stat">
            <div className="home-stat-value">{s.value}</div>
            <div className="home-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Ligues */}
      <div className="home-leagues">
        <div className="home-section-title">Ligues Disponibles</div>
        {loading ? (
          <div className="home-loading">Chargement...</div>
        ) : (
          <div className="home-leagues-list">
            {leagues.map(league => (
              <span key={league} className="home-league-tag">{league}</span>
            ))}
          </div>
        )}
      </div>

      {/* Features */}
      <div className="home-features">
        <div className="home-section-title">Fonctionnalités</div>
        <div className="home-features-grid">
          {features.map(f => (
            <div key={f.title} className="home-feature">
              <div className="home-feature-icon">{f.icon}</div>
              <div>
                <div className="home-feature-title">{f.title}</div>
                <div className="home-feature-desc">{f.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Home;