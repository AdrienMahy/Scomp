import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import ScrapingPage from './pages/ScrapingPage'
import GameListPage from './pages/GameListPage'
import AnalyticsPage from './pages/AnalyticsPage'
import EnrichmentPage from './pages/EnrichmentPage'
import AutomationPage from './pages/AutomationPage'
import OverviewPage from './pages/OverviewPage'
import TaskCenterPage from './pages/TaskCenterPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  const [currentPage, setCurrentPage] = useState('games')
  const [darkMode, setDarkMode] = useState(true)
  const [scope, setScope] = useState(() => {
    try { return JSON.parse(localStorage.getItem('scomp-scope')) || null } catch { return null }
  })

  useEffect(() => {
    if (scope) localStorage.setItem('scomp-scope', JSON.stringify(scope))
  }, [scope])

  // Initialize page from URL query parameter
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const page = params.get('page')
    const taskId = params.get('taskId')
    
    if (taskId && page === 'logs') {
      setCurrentPage('logs')
    } else if (page && ['scraping', 'games', 'game-list', 'analytics', 'logs', 'enrichment', 'automation', 'settings'].includes(page)) {
      setCurrentPage(page)
    }
  }, [])

  // Persist theme preference
  useEffect(() => {
    const saved = localStorage.getItem('theme')
    if (saved) {
      setDarkMode(saved === 'dark')
    }
  }, [])

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  const toggleTheme = () => setDarkMode(!darkMode)

  return (
    <div className="app-shell">
      <Navbar 
        currentPage={currentPage} 
        onPageChange={setCurrentPage}
        darkMode={darkMode}
        onThemeToggle={toggleTheme}
        scope={scope}
        onScopeChange={setScope}
      />
      
      <main className="app-main">
        <div className="page-topline">
          <div>
            <p className="eyebrow">SPORTS DATA OPERATIONS</p>
            <p className="page-context">{scope?.competitionName || 'Select competition'} <span>/</span> {scope?.seasonName || 'Select season'}</p>
          </div>
          <div className="system-state"><span className="status-dot" /> API connected</div>
        </div>
        {currentPage === 'scraping' && <ScrapingPage scope={scope} />}
        {currentPage === 'games' && <OverviewPage onNavigate={setCurrentPage} />}
        {currentPage === 'game-list' && <GameListPage scope={scope} />}
        {currentPage === 'analytics' && <AnalyticsPage />}
        {currentPage === 'logs' && <TaskCenterPage />}
        {currentPage === 'enrichment' && <EnrichmentPage scope={scope} />}
        {currentPage === 'automation' && <AutomationPage onNavigate={setCurrentPage} />}
        {currentPage === 'settings' && <SettingsPage scope={scope} onScopeChange={setScope} />}
      </main>
    </div>
  )
}
