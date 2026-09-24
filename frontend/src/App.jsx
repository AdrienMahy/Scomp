import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import {
  ActivityPage,
  AutomationPage as StatsportAutomationPage,
  LogsPage,
  OverviewPage as StatsportOverviewPage,
  PlayersPage,
  ScrapingPage as StatsportScrapingPage,
  SettingsPage as StatsportSettingsPage,
} from './STATSport'
import {
  AutomationPage,
  EnrichmentPage,
  GameListPage,
  OverviewPage,
  ScrapingPage,
  SettingsPage,
  TaskCenterPage,
} from './SportsDynamics'

export default function App() {
  const [currentPage, setCurrentPage] = useState('games')
  const [project, setProject] = useState(() => localStorage.getItem('scomp-project') || 'tactical')
  const [scope, setScope] = useState(() => {
    try { return JSON.parse(localStorage.getItem('scomp-scope')) || null } catch { return null }
  })

  useEffect(() => {
    if (scope) localStorage.setItem('scomp-scope', JSON.stringify(scope))
  }, [scope])

  useEffect(() => {
    localStorage.setItem('scomp-project', project)
    setCurrentPage(currentPage => project === 'physical'
      ? (currentPage.startsWith('physical-') || currentPage === 'physical' ? currentPage : 'physical-overview')
      : (currentPage.startsWith('physical-') || currentPage === 'physical' ? 'games' : currentPage))
  }, [project])

  const changeProject = (nextProject) => {
    setProject(nextProject)
    setCurrentPage(nextProject === 'physical' ? 'physical-overview' : 'games')
  }

  // Initialize page from URL query parameter
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const page = params.get('page')
    const taskId = params.get('taskId')
    
    if (taskId && page === 'logs') {
      setCurrentPage('logs')
    } else if (page && ['scraping', 'games', 'game-list', 'logs', 'enrichment', 'automation', 'physical', 'physical-overview', 'physical-activity', 'physical-players', 'physical-automation', 'physical-logs', 'physical-settings', 'settings'].includes(page)) {
      if (page === 'physical' || page.startsWith('physical-')) setProject('physical')
      setCurrentPage(page)
    }
  }, [])

  return (
    <div className={`app-shell project-${project}`}>
      <Navbar 
        currentPage={currentPage} 
        onPageChange={setCurrentPage}
        project={project}
        onProjectChange={changeProject}
        scope={scope}
        onScopeChange={setScope}
      />
      
      <main className="app-main">
        <div className="page-topline">
          <div>
            <p className="eyebrow">SPORTS DATA OPERATIONS</p>
            <p className="page-context">{project === 'physical' ? 'STATSports PhysicalData' : `${scope?.competitionName || 'Select competition'} / ${scope?.seasonName || 'Select season'}`}</p>
          </div>
          <div className="system-state"><span className="status-dot" /> API connected</div>
        </div>
        {project === 'tactical' && currentPage === 'scraping' && <ScrapingPage scope={scope} />}
        {project === 'tactical' && currentPage === 'games' && <OverviewPage onNavigate={setCurrentPage} />}
        {project === 'tactical' && currentPage === 'game-list' && <GameListPage scope={scope} />}
        {project === 'tactical' && currentPage === 'logs' && <TaskCenterPage />}
        {project === 'tactical' && currentPage === 'enrichment' && <EnrichmentPage scope={scope} />}
        {project === 'tactical' && currentPage === 'automation' && <AutomationPage onNavigate={setCurrentPage} />}
        {project === 'physical' && currentPage === 'physical-overview' && <StatsportOverviewPage onNavigate={setCurrentPage} />}
        {project === 'physical' && currentPage === 'physical-activity' && <ActivityPage />}
        {project === 'physical' && currentPage === 'physical' && <StatsportScrapingPage />}
        {project === 'physical' && currentPage === 'physical-players' && <PlayersPage />}
        {project === 'physical' && currentPage === 'physical-automation' && <StatsportAutomationPage />}
        {project === 'physical' && currentPage === 'physical-logs' && <LogsPage />}
        {project === 'physical' && currentPage === 'physical-settings' && <StatsportSettingsPage />}
        {project === 'tactical' && currentPage === 'settings' && <SettingsPage scope={scope} onScopeChange={setScope} />}
      </main>
    </div>
  )
}
