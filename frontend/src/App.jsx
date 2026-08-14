import { useState } from 'react'
import GamesList from './pages/GamesList'
import GameDetail from './pages/GameDetail'
import './App.css'

export default function App() {
  const [selectedGameId, setSelectedGameId] = useState(null)

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🎮 Scomp - Games & Output Files</h1>
        <p>Affichage des données stockées en base de données</p>
      </header>

      <div className="app-content">
        {selectedGameId ? (
          <GameDetail 
            gameId={selectedGameId} 
            onBack={() => setSelectedGameId(null)} 
          />
        ) : (
          <GamesList onSelectGame={setSelectedGameId} />
        )}
      </div>

      <footer className="app-footer">
        <p>© 2026 Scomp - Backend API: http://localhost:8001</p>
      </footer>
    </div>
  )
}
