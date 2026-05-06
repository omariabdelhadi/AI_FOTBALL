import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import './Pages.css';

function Tactical() {
  const [leagues, setLeagues]       = useState([]);
  const [teams, setTeams]           = useState([]);
  const [formations, setFormations] = useState([]);
  const [selectedLeague, setLeague] = useState('');
  const [selectedTeam, setTeam]     = useState('');
  const [selectedForm, setForm]     = useState('4-3-3');
  const [result, setResult]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');

  useEffect(() => {
    api.getLeagues().then(data => setLeagues(data.leagues || []));
    api.getFormations().then(data => setFormations(data.formations || []));
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

  const handleAnalyze = async () => {
    if (!selectedTeam) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.analyzeTactical(selectedTeam, selectedForm);
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) { setError(e.message); }
    setLoading(false);
  };

  const posStyle = (pos) => ({
    Goalkeeper: { color: '#f59e0b' }, Defender: { color: '#60a5fa' },
    Midfielder: { color: '#00d4aa' }, Forward:  { color: '#f87171' },
    Attacker:   { color: '#f87171' },
  }[pos] || { color: '#9ca3af' });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-main-title">Analyse Tactique</h1>
        <p className="page-main-subtitle">Trouvez la meilleure formation pour votre équipe</p>
      </div>

      <div className="page-filters">
        <div className="page-filters-title">Paramètres</div>
        <div className="page-filters-grid cols-3">
          <div className="page-field">
            <label>Ligue</label>
            <select value={selectedLeague} onChange={e => setLeague(e.target.value)}>
              <option value="">Choisir une ligue</option>
              {leagues.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <div className="page-field">
            <label>Équipe</label>
            <select value={selectedTeam} onChange={e => setTeam(e.target.value)}
              disabled={!selectedLeague}>
              <option value="">Choisir une équipe</option>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="page-field">
            <label>Formation</label>
            <select value={selectedForm} onChange={e => setForm(e.target.value)}>
              {formations.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
        </div>
        <button className="page-btn" onClick={handleAnalyze}
          disabled={!selectedTeam || loading}>
          {loading ? 'Analyse en cours...' : 'Analyser'}
        </button>
        {error && <div className="page-error">{error}</div>}
      </div>

      {result && (
        <div>
          <div className="page-success">
            Meilleure formation pour {result.team} : <strong>{result.best_formation}</strong>
          </div>

          <div className="page-table-card" style={{ marginBottom: '20px' }}>
            <div className="page-table-header">Comparaison des Formations</div>
            <table className="page-table">
              <thead><tr><th>Formation</th><th>TacticalFit</th><th>Statut</th></tr></thead>
              <tbody>
                {Object.entries(result.formation_scores)
                  .sort((a, b) => b[1] - a[1])
                  .map(([f, score]) => (
                    <tr key={f}>
                      <td style={{ fontWeight: 600 }}>{f}</td>
                      <td style={{ color: '#00d4aa', fontWeight: 600 }}>{score}</td>
                      <td>
                        {f === result.best_formation && (
                          <span className="page-badge green">Recommandée</span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          <div className="page-grid-2">
            <div className="page-table-card">
              <div className="page-table-header">Lineup Optimal — {result.formation}</div>
              <table className="page-table">
                <thead><tr><th>#</th><th>Joueur</th><th>Position</th><th>Rating</th></tr></thead>
                <tbody>
                  {result.optimal_lineup.map((p, i) => (
                    <tr key={i}>
                      <td style={{ color: '#6b7280' }}>{i + 1}</td>
                      <td>{p.name}</td>
                      <td style={{ fontWeight: 600, ...posStyle(p.position) }}>{p.position}</td>
                      <td style={{ color: '#f59e0b', fontWeight: 600 }}>{p.rating}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="page-table-card">
              <div className="page-table-header">TacticalFit — {result.formation}</div>
              <table className="page-table">
                <thead><tr><th>Joueur</th><th>Position</th><th>TacticalFit</th></tr></thead>
                <tbody>
                  {result.tactical_fit.slice(0, 11).map((p, i) => (
                    <tr key={i}>
                      <td>{p.name}</td>
                      <td style={{ fontWeight: 600, ...posStyle(p.position) }}>{p.position}</td>
                      <td style={{ color: '#00d4aa', fontWeight: 600 }}>{p.tactical_fit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Tactical;