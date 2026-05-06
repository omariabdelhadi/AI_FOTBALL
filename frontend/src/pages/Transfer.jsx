import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import './Pages.css';

function Transfer() {
  const [leagues, setLeagues]         = useState([]);
  const [teams, setTeams]             = useState([]);
  const [players, setPlayers]         = useState([]);
  const [selectedLeague, setLeague]   = useState('');
  const [selectedTeam, setTeam]       = useState('');
  const [selectedPlayer, setPlayer]   = useState('');
  const [similar, setSimilar]         = useState(null);
  const [recommended, setRecommended] = useState(null);
  const [position, setPosition]       = useState('');
  const [minRating, setMinRating]     = useState(7.0);
  const [budget, setBudget]           = useState(50);
  const [recLeague, setRecLeague]     = useState('');
  const [loading1, setLoading1]       = useState(false);
  const [loading2, setLoading2]       = useState(false);
  const [error1, setError1]           = useState('');
  const [error2, setError2]           = useState('');

  useEffect(() => {
    api.getLeagues().then(data => setLeagues(data.leagues || []));
  }, []);

  useEffect(() => {
    if (selectedLeague) {
      api.getTeams(selectedLeague).then(data => {
        setTeams(data.teams || []);
        setTeam('');
        setPlayers([]);
      });
    }
  }, [selectedLeague]);

  useEffect(() => {
    if (selectedLeague && selectedTeam) {
      api.getPlayers(selectedLeague, selectedTeam).then(data => {
        setPlayers(data.players || []);
        setPlayer('');
      });
    }
  }, [selectedTeam]);

  const handleSimilar = async () => {
    if (!selectedPlayer) return;
    setLoading1(true);
    setError1('');
    try {
      const data = await api.getSimilarPlayers(selectedPlayer, 5);
      if (data.detail) throw new Error(data.detail);
      setSimilar(data);
    } catch (e) { setError1(e.message); }
    setLoading1(false);
  };

  const handleRecommend = async () => {
    setLoading2(true);
    setError2('');
    try {
      const data = await api.recommendTransfer(position, minRating, budget, recLeague);
      if (data.detail) throw new Error(data.detail);
      setRecommended(data);
    } catch (e) { setError2(e.message); }
    setLoading2(false);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-main-title">Recommandation de Transferts</h1>
        <p className="page-main-subtitle">Trouvez les joueurs similaires et les meilleures recrues</p>
      </div>

      <div className="page-grid-2">
        {/* Similaires */}
        <div className="page-table-card">
          <div className="page-table-header">Joueurs Similaires</div>
          <div style={{ padding: '20px' }}>
            <div className="page-filters-grid cols-2" style={{ marginBottom: '16px' }}>
              <div className="page-field">
                <label>Ligue</label>
                <select value={selectedLeague} onChange={e => setLeague(e.target.value)}>
                  <option value="">Choisir</option>
                  {leagues.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="page-field">
                <label>Équipe</label>
                <select value={selectedTeam} onChange={e => setTeam(e.target.value)}
                  disabled={!selectedLeague}>
                  <option value="">Choisir</option>
                  {teams.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <div className="page-field" style={{ marginBottom: '16px' }}>
              <label>Joueur</label>
              <select value={selectedPlayer} onChange={e => setPlayer(e.target.value)}
                disabled={!selectedTeam}>
                <option value="">Choisir</option>
                {players.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <button className="page-btn" onClick={handleSimilar}
              disabled={!selectedPlayer || loading1}>
              {loading1 ? 'Recherche...' : 'Trouver Similaires'}
            </button>
            {error1 && <div className="page-error">{error1}</div>}
            {similar && (
              <table className="page-table" style={{ marginTop: '16px' }}>
                <thead><tr><th>Joueur</th><th>Position</th><th>Similarité</th><th>Rating</th></tr></thead>
                <tbody>
                  {similar.similar.map((p, i) => (
                    <tr key={i}>
                      <td>{p.player}</td>
                      <td style={{ color: '#6b7280' }}>{p.position}</td>
                      <td style={{ color: '#00d4aa', fontWeight: 600 }}>{p.similarity}</td>
                      <td style={{ color: '#f59e0b', fontWeight: 600 }}>{p.rating}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Recommandations */}
        <div className="page-table-card">
          <div className="page-table-header">Recommandations Recrutement</div>
          <div style={{ padding: '20px' }}>
            <div className="page-filters-grid cols-2" style={{ marginBottom: '16px' }}>
              <div className="page-field">
                <label>Ligue cible</label>
                <select value={recLeague} onChange={e => setRecLeague(e.target.value)}>
                  <option value="">Toutes</option>
                  {leagues.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="page-field">
                <label>Position</label>
                <select value={position} onChange={e => setPosition(e.target.value)}>
                  <option value="">Toutes</option>
                  {['Goalkeeper','Defender','Midfielder','Forward'].map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="page-field" style={{ marginBottom: '12px' }}>
              <label>Rating minimum : {minRating}</label>
              <input type="range" min="6" max="10" step="0.1"
                value={minRating} onChange={e => setMinRating(parseFloat(e.target.value))} />
            </div>
            <div className="page-field" style={{ marginBottom: '16px' }}>
              <label>Budget : {budget}M€</label>
              <input type="range" min="10" max="200" step="10"
                value={budget} onChange={e => setBudget(parseInt(e.target.value))} />
            </div>
            <button className="page-btn" onClick={handleRecommend} disabled={loading2}>
              {loading2 ? 'Recherche...' : 'Recommander'}
            </button>
            {error2 && <div className="page-error">{error2}</div>}
            {recommended && (
              recommended.players.length === 0
                ? <div className="page-error" style={{ marginTop: '12px' }}>Aucun joueur trouvé.</div>
                : <table className="page-table" style={{ marginTop: '16px' }}>
                    <thead><tr><th>Joueur</th><th>Équipe</th><th>Rating</th><th>Valeur</th></tr></thead>
                    <tbody>
                      {recommended.players.map((p, i) => (
                        <tr key={i}>
                          <td>{p.name}</td>
                          <td style={{ color: '#6b7280' }}>{p.team}</td>
                          <td style={{ color: '#f59e0b', fontWeight: 600 }}>{p.rating}</td>
                          <td style={{ color: '#00d4aa', fontWeight: 600 }}>{p.estimated_value}M€</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Transfer;