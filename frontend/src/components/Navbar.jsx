import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Activity, CalendarClock, ChevronDown, ChevronUp, Database, FileEdit, Gauge, LayoutDashboard, ListChecks, Menu, Play, RotateCcw, Settings, Shield, Sparkles, Users, X, Zap } from 'lucide-react'
import { API_BASE } from '../SportsDynamics/api'
import packageJson from '../../package.json'


export default function Navbar({ currentPage, onPageChange, project, onProjectChange, scope, onScopeChange, user }) {
  const [leagues, setLeagues] = useState([])
  const [open, setOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

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
    { id: 'games', label: 'Vue d’ensemble', icon: LayoutDashboard, group: 'Espace de travail' },
    { id: 'game-list', label: 'Matchs', icon: ListChecks, group: 'Espace de travail' },
    { id: 'scraping', label: 'Collecte', icon: Zap, group: 'Espace de travail' },
    { id: 'enrichment', label: 'Enrichissement', icon: Sparkles, group: 'Données' },
    { id: 'automation', label: 'Automatisation', icon: CalendarClock, group: 'Données' },
    { id: 'settings', label: 'Paramètres', icon: Settings, group: 'Système' },
  ]
  const physicalNavigation = [
    { id: 'physical-overview', label: 'Tableau de bord', icon: LayoutDashboard, group: 'Espace de travail' },
    { id: 'physical-activity', label: 'Activités', icon: Gauge, group: 'Espace de travail' },
    { id: 'physical', label: 'Collecte', icon: Zap, group: 'Espace de travail' },
    { id: 'physical-players', label: 'Joueurs', icon: Users, group: 'Données' },
    { id: 'physical-data', label: 'Éditeur de données', icon: FileEdit, group: 'Données' },
    { id: 'physical-deleted-sessions', label: 'Sessions supprimées', icon: RotateCcw, group: 'Données' },
    { id: 'physical-automation', label: 'Automatisation', icon: CalendarClock, group: 'Données' },
    { id: 'physical-settings', label: 'Paramètres', icon: Settings, group: 'Système' },
  ]
  const navigation = project === 'physical' ? physicalNavigation : tacticalNavigation
  if (user?.is_admin) {
    tacticalNavigation.push({ id: 'logs', label: 'Journaux d’activité', icon: Activity, group: 'Système' })
    physicalNavigation.push({ id: 'physical-logs', label: 'Journaux d’activité', icon: Activity, group: 'Système' })
    navigation.push({ id: 'admin-users', label: 'Utilisateurs', icon: Shield, group: 'Système' })
  }

  return (
    <>
      <button className="mobile-nav-trigger" type="button" onClick={() => setMobileOpen(true)} aria-label="Ouvrir le menu de navigation" aria-expanded={mobileOpen}>
        <Menu size={22} aria-hidden="true" />
      </button>
      {mobileOpen && <button className="mobile-nav-backdrop" type="button" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu de navigation" />}
      <nav className={`sidebar ${mobileOpen ? 'is-mobile-open' : ''}`} aria-label="Navigation principale">
        <button className="mobile-nav-close" type="button" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu de navigation">
          <X size={20} aria-hidden="true" />
        </button>
      <div className="brand-lockup">
        <img className="brand-logo" src="/image/logo.png" alt="Scomp" />
        <div><strong>Scomp</strong><span>Data control room</span></div>
      </div>

      <div className="project-switcher" role="group" aria-label="Projet de l’application">
        <span className="project-switcher-label">PROJET</span>
        <div className="project-switcher-options">
          {user.tactical_access && <button type="button" className={project === 'tactical' ? 'is-active' : ''} onClick={() => onProjectChange('tactical')}>
            <span className="project-switcher-mark tactical-mark">T</span>
            <span><strong>TacticalData</strong><small>Intelligence match</small></span>
          </button>}
          {user.statsport_access && <button type="button" className={project === 'physical' ? 'is-active' : ''} onClick={() => onProjectChange('physical')}>
            <span className="project-switcher-mark physical-mark">P</span>
            <span><strong>PhysicalData</strong><small>Pipeline STATSports</small></span>
          </button>}
        </div>
      </div>

      {project === 'tactical' && <div className={`sidebar-season ${open ? 'is-open' : ''}`}>
        <span className="season-label">SAISON ACTIVE</span>
        <button className="season-trigger" type="button" onClick={() => setOpen(!open)} aria-expanded={open}>
          <strong>{scope?.competitionName || 'Chargement...'}</strong>
          <span className="season-trigger-season">{scope?.seasonName || 'Choisir une saison'}{open ? <ChevronUp size={15} aria-hidden="true" /> : <ChevronDown size={15} aria-hidden="true" />}</span>
        </button>
        {open && <div className="season-picker">
          <label>Compétition<span className="season-select-wrap"><select value={scope?.competitionId || ''} onChange={event => { const league = leagues.find(item => item.competitionId === event.target.value); selectScope(event.target.value, league?.Seasons?.[0]?.seasonId) }}><option value="" disabled>Sélectionner une compétition</option>{leagues.map(league => <option key={league.competitionId} value={league.competitionId}>{league.Name}</option>)}</select><ChevronDown size={14} aria-hidden="true" /></span></label>
          <label>Saison<span className="season-select-wrap"><select value={scope?.seasonId || ''} onChange={event => selectScope(scope?.competitionId || activeLeague?.competitionId, event.target.value)}>{(activeLeague?.Seasons || []).map(season => <option key={season.seasonId} value={season.seasonId}>{season.name}</option>)}</select><ChevronDown size={14} aria-hidden="true" /></span></label>
        </div>}
      </div>}

      <div className="nav-groups">
        {['Espace de travail', 'Données', 'Système'].map(group => {
          const items = navigation.filter(item => item.group === group)
          if (!items.length) return null
          return <div className="nav-group" key={group}>
            <span className="nav-group-label">{group}</span>
            {items.map(item => (
              <button
                key={item.id}
                onClick={() => { onPageChange(item.id); setMobileOpen(false) }}
                className={`nav-item ${currentPage === item.id ? 'is-active' : ''}`}
              >
                <span className="nav-icon"><item.icon size={17} strokeWidth={1.9} aria-hidden="true" /></span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        })}
      </div>

      <div className="sidebar-footer">
        <span className="app-version">Scomp v{packageJson.version}</span>
      </div>
      </nav>
    </>
  )
}
