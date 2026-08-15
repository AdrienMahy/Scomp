import { useState } from 'react'
import GamesList from './pages/GamesList'
import GameDetail from './pages/GameDetail'
import TeamsPage from './pages/TeamsPage'
import './App.css'

export default function App() {
  const [selectedGameId, setSelectedGameId] = useState(null)
  const [currentPage, setCurrentPage] = useState('games') // 'games' or 'teams'

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🎮 Scomp - Sports Data Hub</h1>
        <p>Games, Teams & Provider Information</p>
        <nav className="app-nav">
          <button 
            className={`nav-btn ${currentPage === 'games' ? 'active' : ''}`}
            onClick={() => {
              setCurrentPage('games')
              setSelectedGameId(null)
            }}
          >
            📺 Games
          </button>
          <button 
            className={`nav-btn ${currentPage === 'teams' ? 'active' : ''}`}
            onClick={() => setCurrentPage('teams')}
          >
            🏆 Teams
          </button>
        </nav>
      </header>

      <div className="app-content">
        {currentPage === 'games' ? (
          selectedGameId ? (
            <GameDetail 
              gameId={selectedGameId} 
              onBack={() => setSelectedGameId(null)} 
            />
          ) : (
            <GamesList onSelectGame={setSelectedGameId} />
          )
        ) : (
          <TeamsPage />
        )}
      </div>

      <footer className="app-footer">
        <p>© 2026 Scomp - Backend API: http://localhost:8001</p>
      </footer>
    </div>
  )
}
