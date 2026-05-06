import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import './Pages.css';

function Anomaly() {
  const [leagues, setLeagues]       = useState([]);
  const [teams, setTeams]           = useState([]);
  const [selectedLeague, setLeague] = useState('');
  const [selectedTeam, setTeam]     = useState('');
  const [result, setResult]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [filter, setFilter]         = useState('Tous');

  useEffect(() => {
    api.getLeagues().then(data => setLeagues(data.leagues || []));
  }, []);

  useEffect(() => {
    if (selectedLeague) {
      api.getTeams(selectedLeague).then(data => {
        setTeams(data.teams || []);
        setTeam('');
        setResult(null);
      });
    }
  }, [selectedLeague]);

  const handleDetect = async () => {
    if (!selectedLeague) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.detectAnomalies(selectedLeague, selectedTeam);
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const anomalyStyle = (type) => ({
    'Surperformance':   { color: '#00d4aa' },
    'Sous-performance': { color: '#ef4444' },
    'Attention':        { color: '#f59e0b' },
    'Normal':           { color: '#6b7280' },
  }[type] || { color: '#6b7280' });

  const filtered = result?.players.filter(p =>
    filter === 'Tous' ? true : p.anomaly_type === filter
  ) || [];

  const tabs = ['Tous', 'Surperformance', 'Sous-performance', 'Attention', 'Normal'];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-main-title">Détection d'Anomalies</h1>
        <p className="page-main-subtitle">Joueurs qui sur/sous-performent par rapport à la moyenne</p>
      </div>

      <div className="page-filters">
        <div className="page-filters-title">Sélectionner une équipe</div>
        <div className="page-filters-grid cols-2">
          <div className="page-field">
            <label>Ligue</label>
            <select value={selectedLeague} onChange={e => setLeague(e.target.value)}>
              <option value="">Choisir une ligue</option>
              {leagues.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <div className="page-field">
            <label>Équipe (optionnel)</label>
            <select value={selectedTeam} onChange={e => setTeam(e.target.value)}
              disabled={!selectedLeague}>
              <option value="">Toutes les équipes</option>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <button className="page-btn" onClick={handleDetect}
          disabled={!selectedLeague || loading}>
          {loading ? 'Détection en cours...' : 'Détecter les Anomalies'}
        </button>
        {error && <div className="page-error">{error}</div>}
      </div>

      {result && (
        <div>
          <div className="page-metrics cols-5">
            {[
              { label: 'Total',          value: result.total,             color: '#fff' },
              { label: 'Normaux',        value: result.normal,            color: '#6b7280' },
              { label: 'Surperformance', value: result.surperformance,    color: '#00d4aa' },
              { label: 'Sous-perf.',     value: result.sous_performance,  color: '#ef4444' },
              { label: 'Attention',      value: result.attention,         color: '#f59e0b' },
            ].map(m => (
              <div key={m.label} className="page-metric">
                <div className="page-metric-label">{m.label}</div>
                <div className="page-metric-value" style={{ color: m.color, fontSize: '1.6rem' }}>
                  {m.value}
                </div>
              </div>
            ))}
          </div>

          <div className="page-table-card">
            <div className="page-table-header">Joueurs</div>
            <div style={{ padding: '16px 20px 0' }}>
              <div className="page-filter-tabs">
                {tabs.map(t => (
                  <button key={t}
                    className={`page-filter-tab ${filter === t ? 'active' : ''}`}
                    onClick={() => setFilter(t)}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <table className="page-table">
              <thead>
                <tr>
                  <th>Joueur</th>
                  <th>Équipe</th>
                  <th>Position</th>
                  <th>Rating</th>
                  <th>Perf. Score</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{p.name}</td>
                    <td style={{ color: '#6b7280' }}>{p.team}</td>
                    <td>{p.position}</td>
                    <td style={{ color: '#f59e0b', fontWeight: 600 }}>{p.rating}</td>
                    <td>{p.performance_score}</td>
                    <td>
                      <span style={{ fontWeight: 600, ...anomalyStyle(p.anomaly_type) }}>
                        {p.anomaly_type}
                      </span>
                    </td>
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

export default Anomaly;