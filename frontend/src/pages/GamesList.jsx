import { useState, useEffect } from 'react'
import axios from 'axios'
import '../styles/GamesList.css'

export default function GamesList({ onSelectGame }) {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchGames()
  }, [])

  const fetchGames = async () => {
    try {
      setLoading(true)
      const response = await axios.get('http://localhost:8001/games')
      setGames(response.data || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching games:', err)
      setError(`Erreur: ${err.message}. Assurez-vous que le backend est démarré sur http://localhost:8001`)
    } finally {
      setLoading(false)
    }
  }

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
    <div className="games-list-container">
      <h2>📋 Liste des Jeux ({games.length})</h2>
      
      <div className="games-grid">
        {games.map((game) => (
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
                <strong>{game.home_score || '?'}</strong>
                <span>-</span>
                <strong>{game.away_score || '?'}</strong>
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
        ))}
      </div>
    </div>
  )
}
