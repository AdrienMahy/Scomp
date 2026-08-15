import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/TeamsPage.css';

export default function TeamsPage() {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedTeam, setExpandedTeam] = useState(null);

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      setLoading(true);
      const response = await axios.get('http://localhost:8001/teams', {
        params: {
          limit: 100,
          search: searchTerm || undefined
        }
      });
      setTeams(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch teams');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchTeams();
  };

  const toggleExpanded = (teamId) => {
    setExpandedTeam(expandedTeam === teamId ? null : teamId);
  };

  if (loading) return <div className="teams-page"><div className="loading">Loading teams...</div></div>;
  if (error) return <div className="teams-page"><div className="error">{error}</div></div>;

  return (
    <div className="teams-page">
      <div className="teams-header">
        <h1>🏆 Teams & Providers</h1>
        <p>View team information and their data providers</p>
      </div>

      <div className="teams-search">
        <form onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Search teams by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="search-btn">Search</button>
        </form>
        <div className="teams-count">
          {teams.length} {teams.length === 1 ? 'team' : 'teams'} found
        </div>
      </div>

      <div className="teams-grid">
        {teams.map((team) => (
          <div key={team.id} className="team-card">
            <div className="team-header">
              {team.brand && (
                <img
                  src={team.brand}
                  alt={team.name}
                  className="team-logo"
                  onError={(e) => (e.target.style.display = 'none')}
                />
              )}
              <div className="team-info">
                <h3>{team.name}</h3>
                <div className="provider-badge">
                  {team.providers && team.providers.length > 0 ? (
                    <span className="badge-active">
                      {team.providers.length} provider{team.providers.length !== 1 ? 's' : ''}
                    </span>
                  ) : (
                    <span className="badge-empty">No providers</span>
                  )}
                </div>
              </div>
            </div>

            {team.providers && team.providers.length > 0 && (
              <>
                <button
                  className="expand-btn"
                  onClick={() => toggleExpanded(team.id)}
                >
                  {expandedTeam === team.id ? '▼ Hide' : '▶ Show'} Providers
                </button>

                {expandedTeam === team.id && (
                  <div className="providers-list">
                    {team.providers.map((provider, idx) => (
                      <div key={idx} className="provider-item">
                        <div className="provider-name">
                          {provider.provider?.name || 'Unknown'}
                        </div>
                        <div className="provider-id">
                          <strong>ID:</strong> {provider.externalId}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {teams.length === 0 && (
        <div className="no-teams">
          <p>No teams found</p>
        </div>
      )}
    </div>
  );
}
