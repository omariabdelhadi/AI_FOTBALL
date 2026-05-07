import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';
import './Pages.css';

function Simulation() {
  const [teams, setTeams]       = useState([]);
  const [team, setTeam]         = useState('');
  const [opponent, setOpponent] = useState('');
  const [strength, setStrength] = useState(0.5);
  const [home, setHome]         = useState(true);
  const [nSims, setNSims]       = useState(10000);
  const [result, setResult]     = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  useEffect(() => {
    api.getSimulationTeams().then(data => setTeams(data.teams || []));
  }, []);

  const handleSimulate = async () => {
    if (!team || !opponent) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.simulateMatch(team, opponent, strength, home, nSims);
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const chartData = result ? [
    { name: 'Victoire', value: parseFloat(result.prob_win),  color: '#00d4aa' },
    { name: 'Nul',      value: parseFloat(result.prob_draw), color: '#f59e0b' },
    { name: 'Défaite',  value: parseFloat(result.prob_loss), color: '#ef4444' },
  ] : [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-main-title">Simulation Monte Carlo</h1>
        <p className="page-main-subtitle">Simulez le résultat d'un match en milliers de simulations</p>
      </div>

      <div className="page-filters">
        <div className="page-filters-title">Paramètres du match</div>

        <div className="page-filters-grid cols-2">
          <div className="page-field">
            <label>Équipe</label>
            <select value={team} onChange={e => setTeam(e.target.value)}>
              <option value="">Choisir une équipe</option>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="page-field">
            <label>Adversaire</label>
            <select value={opponent} onChange={e => setOpponent(e.target.value)}>
              <option value="">Choisir un adversaire</option>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="page-field">
            <label>Force adversaire : {strength}</label>
            <input type="range" min="0" max="1" step="0.1"
              value={strength} onChange={e => setStrength(parseFloat(e.target.value))} />
            <div className="range-value">
              {strength < 0.4 ? 'Faible' : strength < 0.7 ? 'Moyen' : 'Fort'}
            </div>
          </div>
          <div className="page-field">
            <label>Nombre de simulations</label>
            <select value={nSims} onChange={e => setNSims(parseInt(e.target.value))}>
              {[1000, 5000, 10000, 50000].map(n => (
                <option key={n} value={n}>{n.toLocaleString()}</option>
              ))}
            </select>
          </div>
        </div>

        <label className="page-checkbox-label">
          <input type="checkbox" checked={home}
            onChange={e => setHome(e.target.checked)} />
          Joue à domicile
        </label>

        <br /><br />

        <button className="page-btn" onClick={handleSimulate}
          disabled={!team || !opponent || loading}>
          {loading ? 'Simulation en cours...' : 'Lancer la Simulation'}
        </button>

        {error && <div className="page-error">{error}</div>}
      </div>

      {result && (
        <div>
          <div className="page-metrics cols-3">
            {[
              { label: 'Victoire', value: result.prob_win,  color: '#00d4aa' },
              { label: 'Nul',      value: result.prob_draw, color: '#f59e0b' },
              { label: 'Défaite',  value: result.prob_loss, color: '#ef4444' },
            ].map(m => (
              <div key={m.label} className="page-metric">
                <div className="page-metric-label">{m.label}</div>
                <div className="page-metric-value" style={{ color: m.color }}>
                  {m.value}
                </div>
              </div>
            ))}
          </div>

          <div className="page-table-card">
            <div className="page-table-header">
              Résultats — {result.n_simulations.toLocaleString()} simulations
            </div>
            <div style={{ padding: '20px' }}>
              <div className={result.favori === team ? 'page-success' : 'page-error'}>
                {result.favori === team
                  ? `${team} est favori`
                  : `${opponent} est favori`}
              </div>
              <div className="chart-responsive">
              <BarChart width={500} height={280} data={chartData}
                margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                <YAxis stroke="#6b7280" fontSize={12} tickFormatter={v => `${v}%`} />
                <Tooltip formatter={v => `${v}%`}
                  contentStyle={{ backgroundColor: '#154ec9',
                    border: '1px solid #374151', borderRadius: '8px' }} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {chartData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Bar>
              </BarChart>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Simulation;