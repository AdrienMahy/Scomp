import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import AdminUsersPage from './components/AdminUsersPage'
import AccountMenu from './components/AccountMenu'
import { LoginScreen, PasswordActionScreen } from './components/AuthScreens'
import { initialiseAuth, loadCurrentUser, logout } from './auth'
import {
  ActivityPage,
  AutomationPage as StatsportAutomationPage,
  DeletedSessionsPage,
  LogsPage,
  OverviewPage as StatsportOverviewPage,
  PlayersPage,
  PhysicalDataEditorPage,
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
  const [user, setUser] = useState(undefined)
  const [currentPage, setCurrentPage] = useState('games')
  const [project, setProject] = useState(() => localStorage.getItem('scomp-project') || 'tactical')
  const [physicalEditorSelection, setPhysicalEditorSelection] = useState(null)
  const [scope, setScope] = useState(() => {
    try { return JSON.parse(localStorage.getItem('scomp-scope')) || null } catch { return null }
  })

  useEffect(() => { initialiseAuth(); loadCurrentUser().then(setUser) }, [])

  useEffect(() => {
    if (user && !user.tactical_access && user.statsport_access) setProject('physical')
    if (user && user.tactical_access && !user.statsport_access) setProject('tactical')
  }, [user])

  useEffect(() => {
    if (!user || user.is_admin) return
    if (project === 'tactical' && !user.tactical_access) {
      setProject('physical')
      setCurrentPage('physical-overview')
    } else if (project === 'physical' && !user.statsport_access) {
      setProject('tactical')
      setCurrentPage('games')
    }
  }, [project, user])

  useEffect(() => {
    if (!user || user.is_admin) return
    if (currentPage === 'physical-logs') {
      setProject('physical')
      setCurrentPage('physical-overview')
    } else if (currentPage === 'logs' || currentPage === 'admin-users') {
      const homePage = user.tactical_access ? 'games' : 'physical-overview'
      setProject(user.tactical_access ? 'tactical' : 'physical')
      setCurrentPage(homePage)
    }
  }, [currentPage, user])

  useEffect(() => {
    if (scope) localStorage.setItem('scomp-scope', JSON.stringify(scope))
  }, [scope])

  useEffect(() => {
    localStorage.setItem('scomp-project', project)
    setCurrentPage(currentPage => project === 'physical'
      ? (currentPage.startsWith('physical-') || currentPage === 'physical' ? currentPage : 'physical-overview')
      : (currentPage.startsWith('physical-') || currentPage === 'physical' ? 'games' : currentPage))
  }, [project])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const page = params.get('page')
    const taskId = params.get('taskId')

    if (taskId && page === 'logs') {
      setCurrentPage('logs')
    } else if (page && ['scraping', 'games', 'game-list', 'logs', 'enrichment', 'automation', 'physical', 'physical-overview', 'physical-activity', 'physical-players', 'physical-data', 'physical-deleted-sessions', 'physical-automation', 'physical-logs', 'physical-settings', 'settings'].includes(page)) {
      if (page === 'physical' || page.startsWith('physical-')) setProject('physical')
      setCurrentPage(page)
    }
  }, [])

  const actionParams = new URLSearchParams(window.location.search)
  const passwordToken = actionParams.get('token')
  const passwordAction = window.location.pathname === '/activate' ? 'activation' : window.location.pathname === '/reset-password' ? 'reset' : null
  if (passwordAction && passwordToken) return <PasswordActionScreen mode={passwordAction} token={passwordToken} onComplete={() => { window.history.replaceState({}, '', '/'); setUser(null) }} />
  if (user === undefined) return null
  if (!user) return <LoginScreen onLogin={setUser} />

  const changeProject = (nextProject) => {
    setProject(nextProject)
    setCurrentPage(nextProject === 'physical' ? 'physical-overview' : 'games')
  }

  const navigatePhysical = (page, selection = null) => {
    if (page === 'physical-data') setPhysicalEditorSelection(selection)
    setCurrentPage(page)
  }

  const navigatePage = (page) => {
    if (page === 'physical' || page.startsWith('physical-')) setProject('physical')
    else if (page !== 'admin-users') setProject('tactical')
    setCurrentPage(page)
  }

  return (
    <div className={`app-shell project-${project}`}>
      <Navbar 
        currentPage={currentPage} 
        onPageChange={navigatePage}
        project={project}
        onProjectChange={changeProject}
        scope={scope}
        onScopeChange={setScope}
        user={user}
      />
      
      <main className="app-main">
        <header className="page-topline">
          <div>
            <p className="eyebrow">OPÉRATIONS DE DONNÉES SPORTIVES</p>
            <p className="page-context">{project === 'physical' ? 'STATSports PhysicalData' : `${scope?.competitionName || 'Sélectionner une compétition'} / ${scope?.seasonName || 'Sélectionner une saison'}`}</p>
          </div>
          <div className="page-topline-actions"><AccountMenu user={user} onLogout={() => { logout(); setUser(null) }} /></div>
        </header>
        {user.tactical_access && project === 'tactical' && currentPage === 'scraping' && <ScrapingPage scope={scope} />}
        {project === 'tactical' && currentPage === 'games' && <OverviewPage onNavigate={setCurrentPage} />}
        {project === 'tactical' && currentPage === 'game-list' && <GameListPage scope={scope} />}
        {project === 'tactical' && currentPage === 'logs' && <TaskCenterPage />}
        {project === 'tactical' && currentPage === 'enrichment' && <EnrichmentPage scope={scope} />}
        {project === 'tactical' && currentPage === 'automation' && <AutomationPage onNavigate={setCurrentPage} />}
        {user.statsport_access && project === 'physical' && currentPage === 'physical-overview' && <StatsportOverviewPage onNavigate={setCurrentPage} />}
        {project === 'physical' && currentPage === 'physical-activity' && <ActivityPage onNavigate={navigatePhysical} />}
        {project === 'physical' && currentPage === 'physical' && <StatsportScrapingPage />}
        {project === 'physical' && currentPage === 'physical-players' && <PlayersPage />}
        {project === 'physical' && currentPage === 'physical-data' && <PhysicalDataEditorPage initialSessionId={physicalEditorSelection?.sessionId} initialPlayerId={physicalEditorSelection?.playerId} />}
        {project === 'physical' && currentPage === 'physical-deleted-sessions' && <DeletedSessionsPage />}
        {project === 'physical' && currentPage === 'physical-automation' && <StatsportAutomationPage />}
        {project === 'physical' && currentPage === 'physical-logs' && <LogsPage />}
        {project === 'physical' && currentPage === 'physical-settings' && <StatsportSettingsPage />}
        {project === 'tactical' && currentPage === 'settings' && <SettingsPage scope={scope} onScopeChange={setScope} />}
        {currentPage === 'admin-users' && user.is_admin && <AdminUsersPage />}
      </main>
    </div>
  )
}
