import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { API_BASE } from '../SportsDynamics/api'
import packageJson from '../../package.json'


export default function Navbar({ currentPage, onPageChange, project, onProjectChange, scope, onScopeChange }) {
  const [leagues, setLeagues] = useState([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    axios.get(`${API_BASE}/games/ids-config`).then(response => setLeagues(response.data.leagues || [])).catch(() => setLeagues([]))
  }, [])

  const activeLeague = useMemo(() => leagues.find(league => league.competitionId === scope?.competitionId) || leagues[0], [leagues, scope])
  const activeSeason = activeLeague?.Seasons?.find(season => String(season.seasonId) === String(scope?.seasonId)) || activeLeague?.Seasons?.[0]

  useEffect(() => {
    if (!scope && activeLeague && activeSeason) {
      onScopeChange({ competitionId: activeLeague.competitionId, competitionName: activeLeague.Name, seasonId: String(activeSeason.seasonId), seasonName: activeSeason.name })
    }
  }, [activeLeague, activeSeason, scope, onScopeChange])

  const selectScope = (competitionId, seasonId) => {
    const league = leagues.find(item => item.competitionId === competitionId)
    const season = league?.Seasons?.find(item => String(item.seasonId) === String(seasonId))
    if (league && season) onScopeChange({ competitionId, competitionName: league.Name, seasonId: String(season.seasonId), seasonName: season.name })
  }
  const tacticalNavigation = [
    { id: 'games', label: 'Overview', icon: '⌂', group: 'Workspace' },
    { id: 'game-list', label: 'Matches', icon: '▤', group: 'Workspace' },
    { id: 'scraping', label: 'Scraping', icon: '↯', group: 'Workspace' },
    { id: 'enrichment', label: 'Enrichment', icon: '✦', group: 'Data' },
    { id: 'automation', label: 'Automation', icon: '◌', group: 'Data' },
    { id: 'logs', label: 'Activity logs', icon: '≡', group: 'System' },
    { id: 'settings', label: 'Settings', icon: '⚙', group: 'System' },
  ]
  const physicalNavigation = [
    { id: 'physical-overview', label: 'Overview', icon: '⌂', group: 'Workspace' },
    { id: 'physical-activity', label: 'Activity', icon: '▤', group: 'Workspace' },
    { id: 'physical', label: 'Scraping', icon: '↯', group: 'Workspace' },
    { id: 'physical-players', label: 'Players', icon: '◉', group: 'Data' },
    { id: 'physical-automation', label: 'Automation', icon: '◌', group: 'Data' },
    { id: 'physical-logs', label: 'Activity logs', icon: '≡', group: 'System' },
    { id: 'physical-settings', label: 'Settings', icon: '⚙', group: 'System' },
  ]
  const navigation = project === 'physical' ? physicalNavigation : tacticalNavigation

  return (
    <nav className="sidebar">
      <div className="brand-lockup">
        <img className="brand-logo" src="/image/logo.png" alt="Scomp" />
        <div><strong>Scomp</strong><span>Data control room</span></div>
      </div>

      <div className="project-switcher" role="group" aria-label="Application project">
        <span className="project-switcher-label">PROJECT</span>
        <div className="project-switcher-options">
          <button type="button" className={project === 'tactical' ? 'is-active' : ''} onClick={() => onProjectChange('tactical')}>
            <span className="project-switcher-mark tactical-mark">T</span>
            <span><strong>TacticalData</strong><small>Match intelligence</small></span>
          </button>
          <button type="button" className={project === 'physical' ? 'is-active' : ''} onClick={() => onProjectChange('physical')}>
            <span className="project-switcher-mark physical-mark">P</span>
            <span><strong>PhysicalData</strong><small>STATSports pipeline</small></span>
          </button>
        </div>
      </div>

      {project === 'tactical' && <div className={`sidebar-season ${open ? 'is-open' : ''}`}>
        <span className="season-label">ACTIVE SEASON</span>
        <button className="season-trigger" onClick={() => setOpen(!open)}><strong>{scope?.competitionName || 'Loading...'}</strong><span>{scope?.seasonName || 'Choose a season'} <b>{open ? '⌃' : '⌄'}</b></span></button>
        {open && <div className="season-picker"><label>Competition<select value={scope?.competitionId || ''} onChange={event => { const league = leagues.find(item => item.competitionId === event.target.value); selectScope(event.target.value, league?.Seasons?.[0]?.seasonId) }}><option value="" disabled>Select</option>{leagues.map(league => <option key={league.competitionId} value={league.competitionId}>{league.Name}</option>)}</select></label><label>Season<select value={scope?.seasonId || ''} onChange={event => selectScope(scope?.competitionId || activeLeague?.competitionId, event.target.value)}>{(activeLeague?.Seasons || []).map(season => <option key={season.seasonId} value={season.seasonId}>{season.name}</option>)}</select></label></div>}
      </div>}

      <div className="nav-groups">
        {['Workspace', 'Data', 'System'].map(group => (
          <div className="nav-group" key={group}>
            <span className="nav-group-label">{group}</span>
            {navigation.filter(item => item.group === group).map(item => (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`nav-item ${currentPage === item.id ? 'is-active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
                {item.id === 'automation' && <span className="nav-pulse" />}
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <span className="app-version">Scomp v{packageJson.version}</span>
      </div>
    </nav>
  )
}
