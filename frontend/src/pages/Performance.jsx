// frontend/src/pages/Performance.jsx

import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import './Performance.css';

function Performance() {
  const [leagues, setLeagues]       = useState([]);
  const [teams, setTeams]           = useState([]);
  const [players, setPlayers]       = useState([]);
  const [selectedLeague, setLeague] = useState('');
  const [selectedTeam, setTeam]     = useState('');
  const [selectedPlayer, setPlayer] = useState('');
  const [result, setResult]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');

  useEffect(() => {
    api.getLeagues().then(data => setLeagues(data.leagues || []));
  }, []);

  useEffect(() => {
    if (selectedLeague) {
      api.getTeams(selectedLeague).then(data => {
        setTeams(data.teams || []);
        setTeam('');
        setPlayers([]);
        setPlayer('');
        setResult(null);
      });
    }
  }, [selectedLeague]);

  useEffect(() => {
    if (selectedLeague && selectedTeam) {
      api.getPlayers(selectedLeague, selectedTeam).then(data => {
        setPlayers(data.players || []);
        setPlayer('');
        setResult(null);
      });
    }
  }, [selectedTeam]);

  const handlePredict = async () => {
    if (!selectedPlayer) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.predictPerformance(selectedPlayer);
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const stats = result ? [
    { label: 'Rating',            value: result.current_rating },
    { label: 'Buts',              value: result.goals },
    { label: 'Passes Décisives',  value: result.assists },
    { label: 'Minutes',           value: result.minutes },
    { label: 'Précision Passes',  value: `${result.pass_accuracy}%` },
  ] : [];

  return (
    <div>
      <div className="perf-header">
        <h1 className="perf-title">Prédiction de Performance</h1>
        <p className="perf-subtitle">Estimation du rating futur de chaque joueur</p>
      </div>

      <div className="perf-filters">
        <div className="perf-filters-title">Sélectionner un joueur</div>

        <div className="perf-filters-grid">
          <div className="perf-field">
            <label>Ligue</label>
            <select value={selectedLeague} onChange={e => setLeague(e.target.value)}>
              <option value="">Choisir une ligue</option>
              {leagues.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>

          <div className="perf-field">
            <label>Équipe</label>
            <select
              value={selectedTeam}
              onChange={e => setTeam(e.target.value)}
              disabled={!selectedLeague}
            >
              <option value="">Choisir une équipe</option>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          <div className="perf-field">
            <label>Joueur</label>
            <select
              value={selectedPlayer}
              onChange={e => setPlayer(e.target.value)}
              disabled={!selectedTeam}
            >
              <option value="">Choisir un joueur</option>
              {players.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        </div>

        <button
          className="perf-btn"
          onClick={handlePredict}
          disabled={!selectedPlayer || loading}
        >
          {loading ? 'Prédiction en cours...' : 'Prédire la Performance'}
        </button>

        {error && <div className="perf-error">{error}</div>}
      </div>

      {result && (
        <div>
          <div className="perf-metrics">
            <div className="perf-metric">
              <div className="perf-metric-label">Rating Actuel</div>
              <div className="perf-metric-value">{result.current_rating}</div>
            </div>
            <div className="perf-metric">
              <div className="perf-metric-label">Rating Prédit</div>
              <div className="perf-metric-value" style={{ color: '#00d4aa' }}>
                {result.predicted_rating}
              </div>
            </div>
            <div className="perf-metric">
              <div className="perf-metric-label">Écart</div>
              <div className="perf-metric-value" style={{
                color: result.ecart >= 0 ? '#00d4aa' : '#ef4444'
              }}>
                {result.ecart > 0 ? '+' : ''}{result.ecart}
              </div>
            </div>
            <div className="perf-metric">
              <div className="perf-metric-label">Tendance</div>
              <div className="perf-metric-value" style={{
                fontSize: '1rem',
                color: result.tendance === 'progression' ? '#00d4aa' : '#ef4444'
              }}>
                {result.tendance === 'progression' ? '↑ En hausse' : '↓ En baisse'}
              </div>
            </div>
          </div>

          <div className="perf-stats-card">
            <div className="perf-stats-header">
              <h2>{result.player}</h2>
            </div>
            <div className="perf-stats-meta">
              {result.team} — {result.league} — {result.position}
            </div>
            <table className="perf-table">
              <thead>
                <tr>
                  <th>Statistique</th>
                  <th>Valeur</th>
                </tr>
              </thead>
              <tbody>
                {stats.map(stat => (
                  <tr key={stat.label}>
                    <td>{stat.label}</td>
                    <td className="perf-stat-value">{stat.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default Performance;