// frontend/src/pages/Lineup.jsx

import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import './Lineup.css';

function Lineup() {
  const [leagues, setLeagues]       = useState([]);
  const [teams, setTeams]           = useState([]);
  const [selectedLeague, setLeague] = useState('');
  const [selectedTeam, setTeam]     = useState('');
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
        setResult(null);
      });
    }
  }, [selectedLeague]);

  const handlePredict = async () => {
    if (!selectedTeam) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.predictLineup(selectedTeam);
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const positionStyle = (pos) => {
    const map = {
      Goalkeeper: { color: '#f59e0b', background: 'rgba(245,158,11,0.1)' },
      Defender:   { color: '#60a5fa', background: 'rgba(96,165,250,0.1)' },
      Midfielder: { color: '#00d4aa', background: 'rgba(0,212,170,0.1)' },
      Forward:    { color: '#f87171', background: 'rgba(248,113,113,0.1)' },
      Attacker:   { color: '#f87171', background: 'rgba(248,113,113,0.1)' },
    };
    return map[pos] || { color: '#9ca3af', background: 'rgba(156,163,175,0.1)' };
  };

  const PlayerTable = ({ players, isStarter }) => (
    <div className="lineup-table-card">
      <div className={`lineup-table-header ${isStarter ? 'starters' : 'subs'}`}>
        {isStarter ? 'Titulaires — 11 joueurs' : 'Remplaçants'}
      </div>
      <table className="lineup-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Joueur</th>
            <th>Position</th>
            <th>Rating</th>
            <th>Proba</th>
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => {
            const ps = positionStyle(p.position);
            return (
              <tr key={i}>
                <td className="lineup-rank">{i + 1}</td>
                <td className="lineup-player-name">{p.name}</td>
                <td>
                  <span className="lineup-position" style={ps}>
                    {p.position}
                  </span>
                </td>
                <td className="lineup-rating">{p.rating}</td>
                <td className={isStarter ? 'lineup-proba-starter' : 'lineup-proba-sub'}>
                  {p.proba}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  return (
    <div>
      <div className="lineup-header">
        <h1 className="lineup-title">Lineup Prédit</h1>
        <p className="lineup-subtitle">
          Prédiction des 11 titulaires basée sur le Machine Learning
        </p>
      </div>

      <div className="lineup-filters">
        <div className="lineup-filters-title">Sélectionner une équipe</div>

        <div className="lineup-filters-grid">
          <div className="lineup-field">
            <label>Ligue</label>
            <select value={selectedLeague} onChange={e => setLeague(e.target.value)}>
              <option value="">Choisir une ligue</option>
              {leagues.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>

          <div className="lineup-field">
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
        </div>

        <button
          className="lineup-btn"
          onClick={handlePredict}
          disabled={!selectedTeam || loading}
        >
          {loading ? 'Prédiction en cours...' : 'Prédire le Lineup'}
        </button>

        {error && <div className="lineup-error">{error}</div>}
      </div>

      {result && (
        <div className="lineup-results">
          <PlayerTable players={result.titulaires}  isStarter={true} />
          <PlayerTable players={result.remplacants} isStarter={false} />
        </div>
      )}
    </div>
  );
}

export default Lineup;