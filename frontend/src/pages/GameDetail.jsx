import { useState, useEffect } from 'react'
import axios from 'axios'
import '../styles/GameDetail.css'

export default function GameDetail({ gameId, onBack }) {
  const [game, setGame] = useState(null)
  const [outputFiles, setOutputFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedFileType, setSelectedFileType] = useState(null)

  useEffect(() => {
    fetchGameDetail()
  }, [gameId])

  const fetchGameDetail = async () => {
    try {
      setLoading(true)
      const gameResponse = await axios.get(`http://localhost:8001/games/${gameId}`)
      const game = gameResponse.data
      setGame(game)
      setOutputFiles(game.output_files || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching game detail:', err)
      setError(`Erreur: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="game-detail-container">
        <button onClick={onBack} className="btn-back">← Retour</button>
        <div className="loading">⏳ Chargement des détails...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="game-detail-container">
        <button onClick={onBack} className="btn-back">← Retour</button>
        <div className="error">
          <p>❌ {error}</p>
          <button onClick={fetchGameDetail}>Réessayer</button>
        </div>
      </div>
    )
  }

  if (!game) {
    return (
      <div className="game-detail-container">
        <button onClick={onBack} className="btn-back">← Retour</button>
        <div className="empty">Jeu non trouvé</div>
      </div>
    )
  }

  const fileTypes = [...new Set(outputFiles.map(f => f.file_type))]
  const filteredFiles = selectedFileType 
    ? outputFiles.filter(f => f.file_type === selectedFileType)
    : outputFiles

  return (
    <div className="game-detail-container">
      <button onClick={onBack} className="btn-back">← Retour à la liste</button>

      <div className="detail-header">
        <h2>{game.name}</h2>
        <div className="detail-score">
          <div className="team">
            <p className="team-name">Domicile</p>
            <p className="score">{game.home_score}</p>
          </div>
          <div className="vs">VS</div>
          <div className="team">
            <p className="team-name">Extérieur</p>
            <p className="score">{game.away_score}</p>
          </div>
        </div>
      </div>

      <div className="detail-info">
        <div className="info-item">
          <span className="label">📅 Date</span>
          <span className="value">{new Date(game.starts_at).toLocaleDateString('fr-FR', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}</span>
        </div>
        <div className="info-item">
          <span className="label">🎯 Round</span>
          <span className="value">Round {game.round_name}</span>
        </div>
        <div className="info-item">
          <span className="label">📊 Total Fichiers</span>
          <span className="value badge">{outputFiles.length}</span>
        </div>
      </div>

      {game.lineups && game.lineups.length > 0 && (
        <div className="lineups-section">
          <h3>⚽ Compos</h3>
          <div className="lineups-container">
            {game.lineups.map((lineup, idx) => (
              <div key={idx} className="team-lineup">
                <h4 className={`lineup-position ${lineup.position.toLowerCase()}`}>
                  {lineup.position === 'HOME' ? '🏠 Équipe Domicile' : '🚐 Équipe Extérieure'}
                </h4>
                
                {lineup.players && lineup.players.length > 0 && (
                  <>
                    {/* Titulaires */}
                    {lineup.players.filter(p => p.is_starting).length > 0 && (
                      <div className="players-group">
                        <h5>Titulaires ({lineup.players.filter(p => p.is_starting).length})</h5>
                        <div className="players-list starting">
                          {lineup.players
                            .filter(p => p.is_starting)
                            .sort((a, b) => (a.jersey_number || 0) - (b.jersey_number || 0))
                            .map((player) => (
                              <div key={player.player_id} className="player-card">
                                <div className="player-number">
                                  {player.jersey_number}
                                </div>
                                <div className="player-info">
                                  <p className="player-name">{player.first_name} {player.last_name}</p>
                                  {player.is_captain && <span className="badge captain">👑 Capitaine</span>}
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Remplaçants */}
                    {lineup.players.filter(p => !p.is_starting).length > 0 && (
                      <div className="players-group">
                        <h5>Remplaçants ({lineup.players.filter(p => !p.is_starting).length})</h5>
                        <div className="players-list substitutes">
                          {lineup.players
                            .filter(p => !p.is_starting)
                            .sort((a, b) => (a.jersey_number || 0) - (b.jersey_number || 0))
                            .map((player) => (
                              <div key={player.player_id} className="player-card">
                                <div className="player-number">
                                  {player.jersey_number}
                                </div>
                                <div className="player-info">
                                  <p className="player-name">{player.first_name} {player.last_name}</p>
                                  {player.is_captain && <span className="badge captain">👑 Capitaine</span>}
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="files-section">
        <h3>📁 Fichiers de Sortie ({outputFiles.length})</h3>

        {fileTypes.length > 0 && (
          <div className="file-type-filter">
            <button 
              className={`filter-btn ${!selectedFileType ? 'active' : ''}`}
              onClick={() => setSelectedFileType(null)}
            >
              Tous ({outputFiles.length})
            </button>
            {fileTypes.map(type => (
              <button
                key={type}
                className={`filter-btn ${selectedFileType === type ? 'active' : ''}`}
                onClick={() => setSelectedFileType(type)}
              >
                {type} ({outputFiles.filter(f => f.file_type === type).length})
              </button>
            ))}
          </div>
        )}

        <div className="files-list">
          {filteredFiles.length === 0 ? (
            <p className="empty">Aucun fichier</p>
          ) : (
            filteredFiles.map((file) => (
              <div key={file.id} className="file-item">
                <div className="file-header">
                  <div className="file-info">
                    <span className="file-type-badge">{file.file_type}</span>
                    <p className="file-name">{file.file_name}</p>
                  </div>
                  <div className="file-meta">
                    {file.is_outdated && <span className="outdated">Obsolète</span>}
                    <span className="version">v{file.version}</span>
                  </div>
                </div>

                <div className="file-details">
                  <span className="detail">💾 {file.file_size}</span>
                  <span className="detail">📝 {file.file_name_raw}</span>
                  {file.available && <span className="detail available">✅ Disponible</span>}
                </div>

                {file.url && (
                  <div className="file-url">
                    <p className="url-label">🔗 URL S3:</p>
                    <a 
                      href={file.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="url-link"
                    >
                      {file.url.substring(0, 100)}...
                    </a>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
