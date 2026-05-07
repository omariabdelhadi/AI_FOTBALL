import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import './Pages.css';

function PassNetwork() {
  const [leagues, setLeagues]       = useState([]);
  const [teams, setTeams]           = useState([]);
  const [selectedLeague, setLeague] = useState('');
  const [selectedTeam, setTeam]     = useState('');
  const [result, setResult]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');

  const posColor = {
    Goalkeeper: '#f59e0b', Defender: '#60a5fa',
    Midfielder: '#00d4aa', Attacker:  '#f87171'
  };

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

  const handleAnalyze = async () => {
    if (!selectedTeam) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.analyzePassNetwork(selectedTeam);
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const renderPitch = () => {
    if (!result) return null;
    const posY = { Goalkeeper: 85, Defender: 65, Midfielder: 40, Attacker: 18 };
    const nodes = result.nodes.slice(0, 11);
    const posGroups = {};
    nodes.forEach(n => {
      const pos = n.position || 'Midfielder';
      if (!posGroups[pos]) posGroups[pos] = [];
      posGroups[pos].push(n);
    });
    const coords = {};
    Object.entries(posGroups).forEach(([pos, players]) => {
      const y  = posY[pos] || 40;
      const xs = players.map((_, i) =>
        players.length === 1 ? 50 : 15 + (i * 70 / (players.length - 1))
      );
      players.forEach((p, i) => { coords[p.player] = { x: xs[i], y }; });
    });
    const edges = result.edges.slice(0, 12);
    const maxW  = Math.max(...edges.map(e => e.weight), 1);
    return (
      <svg viewBox="0 0 100 105"
        style={{ width: '100%', maxWidth: '460px',
          backgroundColor: '#14532d', borderRadius: '10px' }}>
        <rect x="5" y="2" width="90" height="101"
          fill="none" stroke="white" strokeWidth="0.5" opacity="0.5"/>
        <line x1="5" y1="52" x2="95" y2="52"
          stroke="white" strokeWidth="0.4" opacity="0.5"/>
        <circle cx="50" cy="52" r="10" fill="none"
          stroke="white" strokeWidth="0.4" opacity="0.5"/>
        {edges.map((edge, i) => {
          const f = coords[edge.from], t = coords[edge.to];
          if (!f || !t) return null;
          return <line key={i} x1={f.x} y1={f.y} x2={t.x} y2={t.y}
            stroke="#00d4aa" strokeWidth={(edge.weight/maxW)*1.5}
            opacity={(edge.weight/maxW)*0.7}/>;
        })}
        {nodes.map((node, i) => {
          const c = coords[node.player];
          if (!c) return null;
          const isKey = node.player === result.key_player;
          return (
            <g key={i}>
              {isKey && <circle cx={c.x} cy={c.y} r="5.5"
                fill="none" stroke="#FFD700" strokeWidth="0.8"/>}
              <circle cx={c.x} cy={c.y} r={isKey ? 4 : 3}
                fill={posColor[node.position] || '#888'}
                stroke="white" strokeWidth="0.5"/>
              <text x={c.x} y={c.y+7} textAnchor="middle"
                fill="white" fontSize="2.8" fontWeight="bold">
                {node.player.split(' ').pop()}
              </text>
            </g>
          );
        })}
      </svg>
    );
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-main-title">Réseau de Passes</h1>
        <p className="page-main-subtitle">Visualisation des connexions entre joueurs</p>
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
            <label>Équipe</label>
            <select value={selectedTeam} onChange={e => setTeam(e.target.value)}
              disabled={!selectedLeague}>
              <option value="">Choisir une équipe</option>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <button className="page-btn" onClick={handleAnalyze}
          disabled={!selectedTeam || loading}>
          {loading ? 'Analyse en cours...' : 'Analyser le Réseau'}
        </button>
        {error && <div className="page-error">{error}</div>}
      </div>

      {result && (
        <div>
          <div className="page-key-player">
            Joueur clé — {result.key_player}
          </div>
          <div className="page-grid-2">
            <div className="page-table-card">
              <div className="page-table-header">{result.team} — Terrain</div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
                  {Object.entries(posColor).map(([pos, color]) => (
                    <span key={pos} style={{ color, fontSize: '0.8rem', fontWeight: 500 }}>
                      ● {pos}
                    </span>
                  ))}
                  <span style={{ color: '#FFD700', fontSize: '0.8rem' }}>○ Joueur clé</span>
                </div>
                {renderPitch()}
              </div>
            </div>

            <div className="page-table-card">
              <div className="page-table-header">Centralité des Joueurs</div>
              <table className="page-table">
                <thead>
                  <tr><th>#</th><th>Joueur</th><th>Position</th><th>Score</th></tr>
                </thead>
                <tbody>
                  {result.centrality.map((p, i) => {
                    const node = result.nodes.find(n => n.player === p.player);
                    const isKey = p.player === result.key_player;
                    return (
                      <tr key={i} style={{ backgroundColor: isKey ? 'rgba(255,215,0,0.05)' : '' }}>
                        <td style={{ color: '#6b7280' }}>{i + 1}</td>
                        <td style={{ color: isKey ? '#FFD700' : '#e5e7eb', fontWeight: isKey ? 700 : 400 }}>
                          {p.player}
                        </td>
                        <td style={{ color: posColor[node?.position] || '#6b7280', fontSize: '0.82rem' }}>
                          {node?.position || '?'}
                        </td>
                        <td style={{ color: '#00d4aa', fontWeight: 600 }}>{p.score}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PassNetwork;