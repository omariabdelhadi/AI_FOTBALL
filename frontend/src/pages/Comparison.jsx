// frontend/src/pages/Comparison.jsx

import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import './Pages.css';

function Comparison() {
  const [leagues, setLeagues]   = useState([]);
  const [teams1, setTeams1]     = useState([]);
  const [teams2, setTeams2]     = useState([]);
  const [players1, setPlayers1] = useState([]);
  const [players2, setPlayers2] = useState([]);
  const [league1, setLeague1]   = useState('');
  const [league2, setLeague2]   = useState('');
  const [team1, setTeam1]       = useState('');
  const [team2, setTeam2]       = useState('');
  const [player1, setPlayer1]   = useState('');
  const [player2, setPlayer2]   = useState('');
  const [result, setResult]     = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  useEffect(() => {
    api.getLeagues().then(data => setLeagues(data.leagues || []));
  }, []);

  useEffect(() => {
    if (league1) {
      api.getTeams(league1).then(data => {
        setTeams1(data.teams || []);
        setTeam1('');
        setPlayers1([]);
        setPlayer1('');
      });
    }
  }, [league1]);

  useEffect(() => {
    if (league2) {
      api.getTeams(league2).then(data => {
        setTeams2(data.teams || []);
        setTeam2('');
        setPlayers2([]);
        setPlayer2('');
      });
    }
  }, [league2]);

  useEffect(() => {
    if (league1 && team1) {
      api.getComparisonPlayers(league1, team1).then(data => {
        setPlayers1(data.players || []);
        setPlayer1('');
      });
    }
  }, [team1]);

  useEffect(() => {
    if (league2 && team2) {
      api.getComparisonPlayers(league2, team2).then(data => {
        setPlayers2(data.players || []);
        setPlayer2('');
      });
    }
  }, [team2]);

  const handleCompare = async () => {
    if (!player1 || !player2) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.comparePlayers(player1, player2);
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  // Radar data — seulement 6 métriques clés
  const radarData = result?.comparison
    .filter(m => ['Rating', 'Buts', 'Passes Décisives',
                  'Précision Passes', 'Impact Défensif', 'Perf. Score']
                  .includes(m.metric))
    .map(m => ({
      metric:  m.metric,
      [player1]: m.p1_norm,
      [player2]: m.p2_norm,
    })) || [];

  const winnerColor = (winner) => ({
    player1: '#00d4aa',
    player2: '#60a5fa',
    draw:    '#6b7280'
  }[winner]);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-main-title">Comparaison de Joueurs</h1>
        <p className="page-main-subtitle">
          Comparez deux joueurs sur leurs statistiques clés
        </p>
      </div>

      {/* Sélection */}
      <div className="page-filters">
        <div className="page-filters-title">Choisir deux joueurs</div>
        <div className="page-grid-2">

          {/* Joueur 1 */}
          <div style={{ borderLeft: '3px solid #00d4aa', paddingLeft: '16px' }}>
            <div style={{ color: '#00d4aa', fontWeight: 700,
              marginBottom: '12px', fontSize: '0.9rem' }}>
              JOUEUR 1
            </div>
            <div className="page-field">
              <label>Ligue</label>
              <select value={league1} onChange={e => setLeague1(e.target.value)}>
                <option value="">Choisir</option>
                {leagues.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div className="page-field">
              <label>Équipe</label>
              <select value={team1} onChange={e => setTeam1(e.target.value)}
                disabled={!league1}>
                <option value="">Choisir</option>
                {teams1.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="page-field">
              <label>Joueur</label>
              <select value={player1} onChange={e => setPlayer1(e.target.value)}
                disabled={!team1}>
                <option value="">Choisir</option>
                {players1.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>

          {/* Joueur 2 */}
          <div style={{ borderLeft: '3px solid #60a5fa', paddingLeft: '16px' }}>
            <div style={{ color: '#60a5fa', fontWeight: 700,
              marginBottom: '12px', fontSize: '0.9rem' }}>
              JOUEUR 2
            </div>
            <div className="page-field">
              <label>Ligue</label>
              <select value={league2} onChange={e => setLeague2(e.target.value)}>
                <option value="">Choisir</option>
                {leagues.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div className="page-field">
              <label>Équipe</label>
              <select value={team2} onChange={e => setTeam2(e.target.value)}
                disabled={!league2}>
                <option value="">Choisir</option>
                {teams2.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="page-field">
              <label>Joueur</label>
              <select value={player2} onChange={e => setPlayer2(e.target.value)}
                disabled={!team2}>
                <option value="">Choisir</option>
                {players2.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>
        </div>

        <br />
        <button className="page-btn" onClick={handleCompare}
          disabled={!player1 || !player2 || loading}>
          {loading ? 'Comparaison en cours...' : 'Comparer les Joueurs'}
        </button>
        {error && <div className="page-error">{error}</div>}
      </div>

      {result && (
        <div>
          {/* Info joueurs */}
          <div className="page-grid-2" style={{ marginBottom: '20px' }}>
            {[
              { p: result.player1, color: '#00d4aa' },
              { p: result.player2, color: '#60a5fa' }
            ].map(({ p, color }) => (
              <div key={p.name} className="page-table-card">
                <div className="page-table-header"
                  style={{ borderLeftColor: color }}>
                  {p.name}
                </div>
                <div style={{ padding: '16px', display: 'flex', gap: '16px',
                  flexWrap: 'wrap' }}>
                  {[
                    { label: 'Équipe',    value: p.team },
                    { label: 'Ligue',     value: p.league },
                    { label: 'Position',  value: p.position },
                    { label: 'Âge',       value: p.age },
                  ].map(item => (
                    <div key={item.label}>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280',
                        textTransform: 'uppercase', marginBottom: '2px' }}>
                        {item.label}
                      </div>
                      <div style={{ color: '#e5e7eb', fontWeight: 600 }}>
                        {item.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Verdict */}
          <div style={{
            background: 'rgba(0,212,170,0.08)',
            border: '1px solid rgba(0,212,170,0.3)',
            borderRadius: '10px',
            padding: '16px 20px',
            marginBottom: '20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <div style={{ color: '#6b7280', fontSize: '0.8rem',
                marginBottom: '4px' }}>VERDICT</div>
              <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '1.2rem' }}>
                {result.verdict === 'Égalité' ? 'Égalité parfaite'
                  : `${result.verdict} est meilleur`}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '24px', textAlign: 'center' }}>
              <div>
                <div style={{ color: '#00d4aa', fontSize: '1.8rem', fontWeight: 800 }}>
                  {result.score.player1}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.78rem' }}>
                  {result.player1.name}
                </div>
              </div>
              <div style={{ color: '#6b7280', fontSize: '1.4rem', alignSelf: 'center' }}>
                vs
              </div>
              <div>
                <div style={{ color: '#60a5fa', fontSize: '1.8rem', fontWeight: 800 }}>
                  {result.score.player2}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.78rem' }}>
                  {result.player2.name}
                </div>
              </div>
            </div>
          </div>

          {/* Radar Chart */}
          <div className="page-table-card" style={{ marginBottom: '20px' }}>
            <div className="page-table-header">Radar — Métriques Clés</div>
            <div style={{ padding: '20px' }} className="chart-responsive">
              <ResponsiveContainer width="100%" height={350} minWidth={400}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#1f2937" />
                  <PolarAngleAxis dataKey="metric"
                    tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]}
                    tick={{ fill: '#6b7280', fontSize: 9 }} />
                  <Radar name={player1} dataKey={player1}
                    stroke="#00d4aa" fill="#00d4aa" fillOpacity={0.2} />
                  <Radar name={player2} dataKey={player2}
                    stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.2} />
                  <Legend wrapperStyle={{ color: '#9ca3af', fontSize: '0.85rem' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827',
                      border: '1px solid #374151', borderRadius: '8px' }}
                    formatter={v => `${v}%`} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Tableau comparatif */}
          <div className="page-table-card">
            <div className="page-table-header">Comparaison Détaillée</div>
            <div className="table-responsive">
              <table className="page-table">
                <thead>
                  <tr>
                    <th style={{ color: '#00d4aa' }}>{player1}</th>
                    <th>Métrique</th>
                    <th style={{ color: '#60a5fa' }}>{player2}</th>
                    <th>Avantage</th>
                  </tr>
                </thead>
                <tbody>
                  {result.comparison.map((m, i) => (
                    <tr key={i}>
                      <td style={{
                        fontWeight: m.winner === 'player1' ? 700 : 400,
                        color: m.winner === 'player1' ? '#00d4aa' : '#e5e7eb'
                      }}>
                        {m.player1}
                      </td>
                      <td style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                        {m.metric}
                      </td>
                      <td style={{
                        fontWeight: m.winner === 'player2' ? 700 : 400,
                        color: m.winner === 'player2' ? '#60a5fa' : '#e5e7eb'
                      }}>
                        {m.player2}
                      </td>
                      <td>
                        <span style={{
                          fontWeight: 600,
                          color: winnerColor(m.winner),
                          fontSize: '0.82rem'
                        }}>
                          {m.winner === 'player1' ? player1
                            : m.winner === 'player2' ? player2
                            : '—'}
                        </span>
                      </td>
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

export default Comparison;