import { useState, useEffect } from 'react'
import axios from 'axios'
import '../styles/GamesList.css'

export default function GamesList({ onSelectGame }) {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedSeason, setSelectedSeason] = useState(null)
  const [selectedCompetition, setSelectedCompetition] = useState(null)
  const [selectedRound, setSelectedRound] = useState(null)

  useEffect(() => {
    fetchGames()
  }, [])

  const fetchGames = async () => {
    try {
      setLoading(true)
      const response = await axios.get('http://localhost:8001/games?limit=100')
      setGames(response.data || [])
      setError(null)
      // Set default selection to first season if available
      if (response.data && response.data.length > 0) {
        setSelectedSeason(response.data[0].season_name)
        
        // Set default to most recent round
        const rounds = [...new Set(response.data.map(g => g.round_name).filter(Boolean))].sort((a, b) => {
          const aNum = parseInt(a)
          const bNum = parseInt(b)
          return isNaN(aNum) || isNaN(bNum) ? b.localeCompare(a) : bNum - aNum
        })
        if (rounds.length > 0) {
          setSelectedRound(rounds[0])
        }
      }
    } catch (err) {
      console.error('Error fetching games:', err)
      setError(`Erreur: ${err.message}. Assurez-vous que le backend est démarré sur http://localhost:8001`)
    } finally {
      setLoading(false)
    }
  }

  // Extract unique seasons and competitions
  const uniqueSeasons = [...new Set(games.map(g => g.season_name).filter(Boolean))]
  const uniqueCompetitions = [...new Set(games.map(g => g.competition_name).filter(Boolean))]
  const uniqueRounds = [...new Set(games.map(g => g.round_name).filter(Boolean))].sort((a, b) => {
    // Sort rounds numerically if they're numbers, otherwise alphabetically
    const aNum = parseInt(a)
    const bNum = parseInt(b)
    return isNaN(aNum) || isNaN(bNum) ? a.localeCompare(b) : aNum - bNum
  })
  
  // Filter games based on selected season, competition and round
  const filteredGames = games.filter(game => {
    const matchSeason = !selectedSeason || game.season_name === selectedSeason
    const matchCompetition = !selectedCompetition || game.competition_name === selectedCompetition
    const matchRound = !selectedRound || game.round_name === selectedRound
    return matchSeason && matchCompetition && matchRound
  })

  if (loading) {
    return (
      <div className="games-list-container">
        <div className="loading">⏳ Chargement des jeux...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="games-list-container">
        <div className="error">
          <p>❌ {error}</p>
          <button onClick={fetchGames}>Réessayer</button>
        </div>
      </div>
    )
  }

  if (games.length === 0) {
    return (
      <div className="games-list-container">
        <div className="empty">
          <p>Aucun jeu trouvé. Lancez d'abord un scrape du backend.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="games-list-wrapper">
      {/* Sidebar avec les journées */}
      <div className="rounds-sidebar">
        <h3>📅 Journées</h3>
        <div className="rounds-list">
          <button
            className={`round-btn ${selectedRound === null ? 'active' : ''}`}
            onClick={() => setSelectedRound(null)}
          >
            Toutes
          </button>
          {uniqueRounds.map(round => (
            <button
              key={round}
              className={`round-btn ${selectedRound === round ? 'active' : ''}`}
              onClick={() => setSelectedRound(round)}
            >
              J{round}
            </button>
          ))}
        </div>
      </div>

      {/* Contenu principal */}
      <div className="games-list-container">
        <h2>📋 Liste des Jeux ({filteredGames.length})</h2>
        
        <div className="filters-section">
          {uniqueSeasons.length > 0 && (
            <div className="filter-group">
              <label htmlFor="season-select">📅 Saison:</label>
              <select 
                id="season-select"
                value={selectedSeason || ''} 
                onChange={(e) => setSelectedSeason(e.target.value || null)}
                className="filter-select"
              >
                <option value="">Toutes les saisons</option>
                {uniqueSeasons.map(season => (
                  <option key={season} value={season}>
                    {season}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          {uniqueCompetitions.length > 1 && (
            <div className="filter-group">
              <label htmlFor="competition-select">🏆 Compétition:</label>
              <select 
                id="competition-select"
                value={selectedCompetition || ''} 
                onChange={(e) => setSelectedCompetition(e.target.value || null)}
                className="filter-select"
              >
                <option value="">Toutes les compétitions</option>
                {uniqueCompetitions.map(competition => (
                  <option key={competition} value={competition}>
                    {competition}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          {(selectedSeason || selectedCompetition || selectedRound) && (
            <button 
              className="btn-reset-filters"
              onClick={() => {
                setSelectedSeason(null)
                setSelectedCompetition(null)
                setSelectedRound(null)
              }}
            >
              ✕ Réinitialiser filtres
            </button>
          )}
        </div>
        
        <div className="games-grid">
          {filteredGames.length === 0 ? (
            <div className="no-results">
              <p>Aucun jeu ne correspond aux filtres sélectionnés.</p>
            </div>
          ) : (
            filteredGames.map((game) => (
              <div 
                key={game.id} 
                className="game-card"
                onClick={() => onSelectGame(game.id)}
              >
                <div className="game-card-header">
                  <h3>{game.name}</h3>
                  <span className="game-round">Round {game.round_name}</span>
                </div>
                
                <div className="game-card-body">
                  <div className="score">
                    <strong>{game.home_score !== null && game.home_score !== undefined ? game.home_score : '?'}</strong>
                    <span>-</span>
                    <strong>{game.away_score !== null && game.away_score !== undefined ? game.away_score : '?'}</strong>
                  </div>
                  
                  <div className="game-meta">
                    <p>📅 {new Date(game.starts_at).toLocaleDateString('fr-FR')}</p>
                    <p>📊 Fichiers: <span className="badge">{game.output_files?.length || 0}</span></p>
                  </div>
                </div>
                
                <div className="game-card-footer">
                  <button className="btn-details">Détails →</button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
