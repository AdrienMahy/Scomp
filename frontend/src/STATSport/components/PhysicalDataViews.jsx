import { useEffect, useState } from 'react'
import axios from 'axios'
import { Activity as ActivityIcon, ArrowLeft, CalendarClock, CalendarDays, ChevronDown, Fingerprint, Pencil, Plus, Save, Search, Trash2, UsersRound, X } from 'lucide-react'
import { API_BASE } from '../api'

function utcToday() { return new Date().toISOString().slice(0, 10) }
function shiftDate(days) { const value = new Date(`${utcToday()}T00:00:00Z`); value.setUTCDate(value.getUTCDate() + days); return value.toISOString().slice(0, 10) }
function formatDate(value) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }) }
function formatDashboardDate(value, includeTime = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const day = String(date.getDate()).padStart(2, '0')
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  if (!includeTime) return `${day}-${month}-${year}`
  return `${day}-${month}-${year} ${date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`
}
function formatTime(value) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) }
function formatCalendarDate(value) { if (!value) return '—'; return new Date(`${value}T00:00:00Z`).toLocaleDateString('fr-FR', { dateStyle: 'long', timeZone: 'UTC' }) }
function dateKey(value) { return value ? String(value).slice(0, 10) : '' }
function activityPlayerName(player) { return player.display_name || `${player.first_name || ''} ${player.last_name || ''}`.trim() || 'Joueur sans nom' }
function squadDisplayName(squad) { return squad?.name?.trim() || (squad?.external_id ? `Équipe ${String(squad.external_id).slice(0, 8)}` : 'Équipe sans nom') }
const DEFAULT_SQUAD_COLORS = ['#55d6c0', '#f2b84b', '#e86a92', '#8da7ff', '#c38cff', '#f28f5b', '#78d46d']
function readSquadColors() { try { return JSON.parse(localStorage.getItem('physical-squad-colors') || '{}') } catch { return {} } }
function colorForSquad(squad, index = 0, colors = {}) { return colors[squad?.id] || DEFAULT_SQUAD_COLORS[index % DEFAULT_SQUAD_COLORS.length] }
function groupPlayersByPosition(players = []) { return players.reduce((groups, player) => { const position = player.primary_position || player.secondary_position || 'Position non renseignée'; (groups[position] ||= []).push(player); return groups }, {}) }
function sortDrillsByStartTime(drills = []) { return [...drills].sort((first, second) => { const firstTime = first.start_time ? Date.parse(first.start_time) : Number.POSITIVE_INFINITY; const secondTime = second.start_time ? Date.parse(second.start_time) : Number.POSITIVE_INFINITY; return (Number.isNaN(firstTime) ? Number.POSITIVE_INFINITY : firstTime) - (Number.isNaN(secondTime) ? Number.POSITIVE_INFINITY : secondTime) }) }

function Header({ eyebrow, title, detail, children, className = '' }) {
  return <header className={`physical-hero ${className}`}><div><p className="eyebrow physical-eyebrow">{eyebrow}</p><h1>{title}</h1><p>{detail}</p></div>{children}</header>
}
function Panel({ kicker, title, count, children }) {
  return <section className="physical-panel"><div className="physical-panel-heading"><div><span className="physical-kicker">{kicker}</span><h2>{title}</h2></div>{count !== undefined && <span className="physical-count">{count}</span>}</div>{children}</section>
}
function Empty({ children = 'Aucune donnée disponible pour le moment.' }) { return <div className="physical-empty">{children}</div> }

export function usePhysicalCatalog() {
  const [sessions, setSessions] = useState([]); const [players, setPlayers] = useState([]); const [squads, setSquads] = useState([]); const [seasons, setSeasons] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  const load = async () => { try { const [sessionResponse, playerResponse, squadResponse, seasonResponse] = await Promise.all([axios.get(`${API_BASE}/physical/sessions?limit=100`), axios.get(`${API_BASE}/physical/players?limit=100`), axios.get(`${API_BASE}/physical/squads`), axios.get(`${API_BASE}/physical/seasons`)]); setSessions(sessionResponse.data || []); setPlayers(playerResponse.data || []); setSquads(squadResponse.data || []); setSeasons(seasonResponse.data || []); setError('') } catch (requestError) { setError(requestError.response?.data?.detail || requestError.message) } finally { setLoading(false) } }
  useEffect(() => { load() }, [])
  return { sessions, players, squads, seasons, loading, error, reload: load }
}

function ActivityRows({ sessions }) {
  return sessions.length ? <div className="physical-recent-activities">
    <div className="physical-recent-activity-heading"><span>Activité</span><span>Date de session</span><span>Date du process</span><span>ID activité STATSports</span></div>
    {sessions.map(session => <div className="physical-recent-activity-row" key={session.activity_id}>
      <strong>{session.activity_name || 'Activité sans nom'}</strong>
      <span>{formatDashboardDate(session.session_date)}</span>
      <span>{formatDashboardDate(session.processed_at, true)}</span>
      <code title={session.activity_id}>{session.activity_id}</code>
    </div>)}
  </div> : <Empty>Aucune activité PhysicalData n’a encore été importée.</Empty>
}

export function Overview({ catalog, onNavigate }) {
  const { sessions, players, squads } = catalog
  const [overview, setOverview] = useState(null)
  const [overviewError, setOverviewError] = useState('')
  const [overviewLoading, setOverviewLoading] = useState(true)

  useEffect(() => {
    axios.get(`${API_BASE}/physical/overview`)
      .then(response => setOverview(response.data))
      .catch(requestError => setOverviewError(requestError.response?.data?.detail || 'Impossible de charger le tableau de bord.'))
      .finally(() => setOverviewLoading(false))
  }, [])

  const count = value => overviewLoading ? '…' : overviewError ? '—' : Number(value || 0).toLocaleString('fr-FR')

  return <div className="physical-page">
    <Header eyebrow="PHYSICALDATA / STATSports" title="Tableau de bord STATSports" detail="Activités traitées, joueurs enregistrés et dernières mises à jour de la base." className="dashboard-hero" />
    <div className="physical-metrics dashboard-metrics">
      <div><span>Activités totales</span><strong>{count(overview?.activity_total)}</strong><small>activités actives en base</small></div>
      <div><span>Joueurs</span><strong>{count(overview?.player_total)}</strong><small>joueurs enregistrés</small></div>
      <div><span>Activités aujourd’hui</span><strong>{count(overview?.activity_today)}</strong><small>date de session du jour</small></div>
      <div><span>Équipes</span><strong>{Number(squads.length).toLocaleString('fr-FR')}</strong><small>disponibles pour le filtrage</small></div>
    </div>
    {overviewError && <p className="physical-alert" role="alert">{overviewError}</p>}
    <div className="physical-overview-grid dashboard-overview-grid">
      <Panel kicker="Espace de travail" title="Actions rapides"><div className="physical-actions"><button onClick={() => onNavigate('physical')}><b>↯</b><span><strong>Lancer une collecte</strong><small>Importer par date, période ou identifiant d’activité</small></span><i>→</i></button><button onClick={() => onNavigate('physical-activity')}><b>▤</b><span><strong>Consulter les activités</strong><small>Filtrer les sessions par date ou équipe</small></span><i>→</i></button><button onClick={() => onNavigate('physical-players')}><b>◉</b><span><strong>Parcourir les joueurs</strong><small>Consulter les profils importés</small></span><i>→</i></button><button onClick={() => onNavigate('physical-data')}><b>✎</b><span><strong>Éditeur manuel</strong><small>Modifier manuellement les métriques des exercices</small></span><i>→</i></button></div></Panel>
      <Panel kicker="Historique des traitements" title="Dernière activité" count={`${overview?.recent_activities?.length || 0} / 10`}>
        {overviewLoading ? <Empty>Chargement des activités récentes…</Empty> : overviewError ? <Empty>Les dernières activités ne sont pas disponibles.</Empty> : <ActivityRows sessions={overview?.recent_activities || []} />}
      </Panel>
    </div>
  </div>
}

export function Activity({ catalog: sourceCatalog, onNavigate }) {
  const [teams, setTeams] = useState([])
  const [date, setDate] = useState(utcToday()); const [teamName, setTeamName] = useState(''); const [sessions, setSessions] = useState(sourceCatalog.sessions.map(session => ({ ...session, squad_id: session.team_name?.trim().toLocaleLowerCase() || '' }))); const [loading, setLoading] = useState(false); const [month, setMonth] = useState(dateKey(sourceCatalog.sessions[0]?.session_date).slice(0, 7) || utcToday().slice(0, 7)); const [selected, setSelected] = useState(null); const [detail, setDetail] = useState(null); const [detailLoading, setDetailLoading] = useState(false); const [reprocessState, setReprocessState] = useState(null); const [squadColors, setSquadColors] = useState(readSquadColors)
  const squadId = teamName
  const setSquadId = setTeamName
  const catalog = { ...sourceCatalog, squads: teams.map(team => ({ id: team.name.trim().toLocaleLowerCase(), name: team.name, external_id: team.name })) }
  useEffect(() => {
    axios.get(`${API_BASE}/physical/teams`)
      .then(response => setTeams(response.data || []))
      .catch(() => setTeams([]))
  }, [])
  useEffect(() => {
    setSessions(sourceCatalog.sessions.map(session => ({ ...session, squad_id: session.team_name?.trim().toLocaleLowerCase() || '' })))
    if (sourceCatalog.sessions[0]?.session_date) {
      const latestSessionDate = dateKey(sourceCatalog.sessions[0].session_date)
      setDate(currentDate => currentDate || latestSessionDate)
      setMonth(utcToday().slice(0, 7))
    }
  }, [sourceCatalog.sessions])
  useEffect(() => {
    const calendarStart = `${month}-01`
    const calendarDate = new Date(`${calendarStart}T00:00:00Z`)
    const calendarEnd = new Date(Date.UTC(calendarDate.getUTCFullYear(), calendarDate.getUTCMonth() + 1, 0)).toISOString().slice(0, 10)
    const params = new URLSearchParams({ start_date: calendarStart, end_date: calendarEnd, limit: '500' })
    if (teamName) params.set('team_name', teamName)
    setLoading(true)
    axios.get(`${API_BASE}/physical/sessions?${params}`)
      .then(response => setSessions((response.data || []).map(session => ({ ...session, squad_id: session.team_name?.trim().toLocaleLowerCase() || '' }))))
      .finally(() => setLoading(false))
  }, [month, teamName, sourceCatalog.sessions])
  const filter = async event => { event.preventDefault(); setLoading(true); try { const params = new URLSearchParams({ limit: '100' }); if (date) params.set('session_date', date); if (teamName) params.set('team_name', teamName); const response = await axios.get(`${API_BASE}/physical/sessions?${params}`); const values = (response.data || []).map(session => ({ ...session, squad_id: session.team_name?.trim().toLocaleLowerCase() || '' })); setSessions(values); if (values[0]) setMonth(dateKey(values[0].session_date).slice(0, 7)) } finally { setLoading(false) } }
  const openActivity = async session => { setSelected(session); setDetail(null); setDetailLoading(true); try { const response = await axios.get(`${API_BASE}/physical/activities/${session.activity_id}`); const drills = sortDrillsByStartTime(response.data.drills).map(drill => ({ ...drill, primary_label: `${formatTime(drill.start_time)} → ${formatTime(drill.end_time)}`, secondary_label: null, tertiary_label: null, session_type: null })); setDetail({ ...response.data, drills }) } catch { setDetail({ activity: session, players: [], drills: [] }) } finally { setDetailLoading(false) } }
  const reprocessActivity = async () => {
    if (!selected || reprocessState?.status === 'loading') return
    setReprocessState({ status: 'loading' })
    try {
      const response = await axios.post(`${API_BASE}/physical/scraping/activity`, null, {
        params: { session_date: dateKey(selected.session_date), activity_id: selected.activity_id },
      })
      setReprocessState({ status: 'success', taskId: response.data.task_id })
    } catch (error) {
      setReprocessState({ status: 'error', message: error.response?.data?.detail || error.message })
    }
  }
  const calendarDate = new Date(`${month}-01T00:00:00Z`); const firstWeekday = (calendarDate.getUTCDay() + 6) % 7; const daysInMonth = new Date(Date.UTC(calendarDate.getUTCFullYear(), calendarDate.getUTCMonth() + 1, 0)).getUTCDate(); const cells = Array.from({ length: Math.ceil((firstWeekday + daysInMonth) / 7) * 7 }, (_, index) => { const day = index - firstWeekday + 1; return day > 0 && day <= daysInMonth ? `${month}-${String(day).padStart(2, '0')}` : null }); const monthLabel = calendarDate.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric', timeZone: 'UTC' }); const sessionsByDate = sessions.reduce((groups, session) => { const key = dateKey(session.session_date); (groups[key] ||= []).push(session); return groups }, {})
  const shiftMonth = amount => { const next = new Date(Date.UTC(calendarDate.getUTCFullYear(), calendarDate.getUTCMonth() + amount, 1)); setMonth(next.toISOString().slice(0, 7)) }
  useEffect(() => {
    const legendEntries = Array.from(document.querySelectorAll('.physical-squad-legend > span'))
    const sessionButtons = Array.from(document.querySelectorAll('.physical-calendar-activity'))
    let selectedTeamName = ''
    const resetHighlight = () => {
      legendEntries.forEach(entry => { entry.style.opacity = ''; entry.style.fontWeight = '' })
      sessionButtons.forEach(button => { button.style.opacity = ''; button.style.transform = '' })
    }
    const highlightSquad = event => {
      const entryIndex = legendEntries.indexOf(event.currentTarget)
      const team = catalog.squads[entryIndex]
      if (!team) return
      selectedTeamName = selectedTeamName === team.id ? '' : team.id
      if (!selectedTeamName) { resetHighlight(); return }
      legendEntries.forEach((entry, index) => { entry.style.opacity = index === entryIndex ? '1' : '.4'; entry.style.fontWeight = index === entryIndex ? '800' : '' })
      sessionButtons.forEach(button => {
        const session = sessions.find(item => item.activity_name === button.title)
        const isMatch = session?.team_name?.trim().toLocaleLowerCase() === selectedTeamName
        button.style.opacity = isMatch ? '1' : '.22'
        button.style.transform = isMatch ? 'scale(1.02)' : ''
      })
    }
    legendEntries.forEach(entry => entry.addEventListener('click', highlightSquad))
    return () => legendEntries.forEach(entry => entry.removeEventListener('click', highlightSquad))
  }, [catalog.squads, sessions])
  useEffect(() => {
    const today = utcToday()
    const calendarDays = Array.from(document.querySelectorAll('.physical-calendar-day'))
    calendarDays.forEach(day => day.classList.remove('is-today'))
    if (month !== today.slice(0, 7)) return
    const todayNumber = String(Number(today.slice(-2)))
    calendarDays.forEach(day => {
      if (day.querySelector(':scope > b')?.textContent === todayNumber) day.classList.add('is-today')
    })
    return () => calendarDays.forEach(day => day.classList.remove('is-today'))
  }, [month])
  return <div className="physical-page"><Header eyebrow="PHYSICALDATA / ACTIVITY" title="Calendrier des activités" detail="Parcourez les activités importées par date, équipe et détail de session." /><Panel kicker="Filtres" title="Rechercher une activité"><form className="physical-filter-form" onSubmit={filter}><label>Date de session<input type="date" value={date} onChange={event => setDate(event.target.value)} /></label><label>Squad<select value={squadId} onChange={event => setSquadId(event.target.value)}><option value="">Toutes les équipes</option>{catalog.squads.map(squad => <option key={squad.id} value={squad.id}>{squad.name || squad.external_id}</option>)}</select></label><button className="physical-primary-button" disabled={loading}>{loading ? 'Chargement...' : 'Appliquer les filtres'}</button></form></Panel><Panel kicker="Calendrier" title={monthLabel} count={`${sessions.length} activité(s)`}><div className="physical-calendar-toolbar"><button type="button" onClick={() => shiftMonth(-1)} aria-label="Mois précédent">←</button><button type="button" onClick={() => setMonth(utcToday().slice(0, 7))}>Aujourd’hui</button><button type="button" onClick={() => shiftMonth(1)} aria-label="Mois suivant">→</button></div><div className="physical-squad-legend">{catalog.squads.map((squad, index) => <span key={squad.id}><i style={{ backgroundColor: colorForSquad(squad, index, squadColors) }} />{squad.name || squad.external_id}</span>)}</div><div className="physical-calendar-grid"><div className="physical-calendar-weekdays">{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => <span key={day}>{day}</span>)}</div><div className="physical-calendar-days">{cells.map((key, index) => <div className={`physical-calendar-day ${key === date ? 'is-filtered' : ''}`} key={key || `empty-${index}`}>{key && <><b>{Number(key.slice(-2))}</b><div>{(sessionsByDate[key] || []).map(session => { const squadIndex = catalog.squads.findIndex(squad => squad.id === session.squad_id); return <button type="button" className="physical-calendar-activity" style={{ '--activity-color': colorForSquad(catalog.squads[squadIndex], squadIndex, squadColors) }} key={`${session.activity_id}-${session.id}`} onClick={() => openActivity(session)} title={session.activity_name || 'Activité sans nom'}><i />{session.activity_name || 'Activité sans nom'}</button> })}</div></>}</div>)}</div></div></Panel>{selected && <><button className="offcanvas-backdrop" type="button" aria-label="Fermer le détail de l’activité" onClick={() => setSelected(null)} /><aside className="match-offcanvas physical-activity-offcanvas"><div className="offcanvas-header"><div><span className="physical-kicker">Détail de l’activité</span><h3>{detail?.activity?.activity_name || selected.activity_name || 'Activité sans nom'}</h3></div><button className="offcanvas-close" type="button" onClick={() => setSelected(null)} aria-label="Fermer">×</button></div><div className="physical-activity-actions"><button className="offcanvas-scrape-button" type="button" disabled={detailLoading || !detail?.players?.length} onClick={() => onNavigate('physical-data', { sessionId: selected.id, playerId: detail?.players?.[0]?.id })}><Pencil size={14} /> Éditeur manuel des données</button><button className="offcanvas-scrape-button" type="button" disabled={detailLoading || reprocessState?.status === 'loading'} onClick={reprocessActivity}>{reprocessState?.status === 'loading' ? 'Reprocessing...' : '↻ Reprocess activity'}</button>{reprocessState?.status === 'success' && <span className="offcanvas-task-message success">Reprocess queued.</span>}{reprocessState?.status === 'error' && <span className="offcanvas-task-message error">{reprocessState.message}</span>}</div>{detailLoading ? <Empty>Loading activity details...</Empty> : <><div className="physical-activity-facts"><span><b>Start / end</b>{formatDate(detail?.activity?.start_time)}<br />{formatDate(detail?.activity?.end_time)}</span><span><b>Identifiant d’activité</b>{detail?.activity?.activity_id}</span><span><b>ShareDate</b>{formatDate(detail?.activity?.share_date)}</span><span><b>Processed</b>{formatDate(detail?.activity?.processed_at)}</span></div><div className="offcanvas-section"><span className="offcanvas-label">Drills · {detail?.drills?.length || 0}</span>{detail?.drills?.length ? <div className="physical-detail-list">{detail.drills.map((drill, index) => <div key={`${drill.drill_name}-${index}`}><strong>{drill.drill_name || 'Unnamed drill'}</strong><small>{[drill.primary_label, drill.secondary_label, drill.tertiary_label].filter(Boolean).join(' · ') || drill.session_type || '—'}</small></div>)}</div> : <Empty>No drills recorded.</Empty>}</div><div className="offcanvas-section"><span className="offcanvas-label">Players · {detail?.players?.length || 0}</span>{detail?.players?.length ? <div className="physical-player-groups">{Object.entries(groupPlayersByPosition(detail.players)).map(([position, players]) => <div className="physical-player-group" key={position}><span className="physical-player-group-title">{position} · {players.length}</span><div className="physical-detail-list">{players.map(player => <div key={player.id}><strong>{activityPlayerName(player)}</strong><small>{player.active_squad_name || '—'}</small></div>)}</div></div>)}</div> : <Empty>No players recorded.</Empty>}</div></>}</aside></>}</div>
}

export function Scraping({ onImported = () => {} }) {
  const [mode, setMode] = useState('daily'); const [shareDate, setShareDate] = useState(utcToday()); const [startDate, setStartDate] = useState(shiftDate(-7)); const [endDate, setEndDate] = useState(utcToday()); const [sessionDate, setSessionDate] = useState(utcToday()); const [activityId, setActivityId] = useState(''); const [teamName, setTeamName] = useState(''); const [teams, setTeams] = useState([]); const [running, setRunning] = useState(false); const [result, setResult] = useState(null)
  useEffect(() => { axios.get(`${API_BASE}/physical/teams`).then(response => setTeams(response.data || [])).catch(() => setTeams([])) }, [])
  const run = async event => { event.preventDefault(); setRunning(true); setResult(null); try { let response; if (mode === 'daily') response = await axios.post(`${API_BASE}/physical/scraping/automation/run`, null, { params: { share_date: shareDate, team_name: teamName || undefined } }); else if (mode === 'range') response = await axios.post(`${API_BASE}/physical/scraping/range-date`, null, { params: { start_date: startDate, end_date: endDate, team_name: teamName || undefined } }); else response = await axios.post(`${API_BASE}/physical/scraping/activity`, null, { params: { session_date: sessionDate, activity_id: activityId } }); setResult({ status: 'success', data: response.data }); onImported() } catch (requestError) { setResult({ status: 'error', message: requestError.response?.data?.detail || requestError.message }) } finally { setRunning(false) } }
  const setRange = (days) => { setStartDate(shiftDate(-days + 1)); setEndDate(utcToday()) }
  const modes = [
    { key: 'daily', label: 'Date de partage', detail: 'Récupérer le flux publié ce jour', Icon: CalendarDays },
    { key: 'range', label: 'Période de dates', detail: 'Importer plusieurs journées', Icon: CalendarClock },
    { key: 'activity', label: 'Par identifiant', detail: 'Cibler une activité précise', Icon: Fingerprint },
  ]
  return <div className="physical-page physical-scrape-page">
    <Header eyebrow="PHYSICALDATA / COLLECTE" title="Collecte des activités" detail="Choisissez une date, une période ou une activité à importer." />
    <section className="physical-collection-workspace">
      <div className="physical-tabs physical-scrape-tabs" role="group" aria-label="Mode de collecte">
        {modes.map(({ key, label, detail, Icon }) => <button key={key} className={mode === key ? 'is-active' : ''} type="button" aria-pressed={mode === key} onClick={() => setMode(key)}>
          <Icon size={17} strokeWidth={1.9} aria-hidden="true" />
          <span><strong>{label}</strong><small>{detail}</small></span>
        </button>)}
      </div>
      <form className="physical-form physical-scrape-form" onSubmit={run}>
        {mode === 'daily' && <div className="physical-calendar-field">
          <label>Date de partage (UTC)<input type="date" value={shareDate} onChange={event => setShareDate(event.target.value)} required /></label>
          <div className="physical-date-shortcuts"><button type="button" onClick={() => setShareDate(utcToday())}>Aujourd’hui</button><button type="button" onClick={() => setShareDate(shiftDate(-1))}>Hier</button></div>
        </div>}
        {mode === 'range' && <div className="physical-calendar-field">
          <div className="physical-field-row"><label>Date de début<input type="date" max={endDate} value={startDate} onChange={event => setStartDate(event.target.value)} required /></label><label>Date de fin<input type="date" min={startDate} value={endDate} onChange={event => setEndDate(event.target.value)} required /></label></div>
          <div className="physical-date-shortcuts"><button type="button" onClick={() => setRange(1)}>Aujourd’hui</button><button type="button" onClick={() => setRange(2)}>2 jours</button><button type="button" onClick={() => setRange(7)}>7 jours</button><button type="button" onClick={() => setRange(30)}>30 jours</button></div>
        </div>}
        {mode !== 'activity' && <label className="physical-squad-filter"><span>Équipe à collecter</span><span className="physical-team-select"><select value={teamName} onChange={event => setTeamName(event.target.value)}><option value="">Toutes les équipes</option>{teams.map(team => <option key={team.name} value={team.name}>{team.name}</option>)}</select><ChevronDown size={16} aria-hidden="true" /></span><small>La collecte sera limitée à l’équipe choisie.</small></label>}
        {mode === 'activity' && <div className="physical-field-row physical-scrape-activity-fields"><label>Date de session<input type="date" value={sessionDate} onChange={event => setSessionDate(event.target.value)} required /></label><label>Identifiant d’activité STATSports<input value={activityId} onChange={event => setActivityId(event.target.value)} placeholder="UUID de l’activité" required /></label></div>}
        <div className="physical-form-footer"><span>Chaque activité est traitée et enregistrée individuellement.</span><button className="physical-primary-button" disabled={running}><ActivityIcon size={16} aria-hidden="true" />{running ? 'Collecte en cours…' : 'Lancer la collecte'}<b>→</b></button></div>
      </form>
    </section>
    {result && <div className={`physical-result ${result.status}`} role={result.status === 'error' ? 'alert' : 'status'}>
      <div><strong>{result.status === 'success' ? 'Collecte terminée' : 'Échec de la collecte'}</strong><span>{result.status === 'success' ? `${result.data.found ?? 0} trouvée(s) · ${result.data.inserted ?? 0} nouvelle(s) · ${result.data.updated ?? 0} mise(s) à jour · ${result.data.failed ?? 0} échec(s)` : result.message}</span></div>
    </div>}
  </div>
}

export function Players() {
  const [teams, setTeams] = useState([])
  const [teamsLoading, setTeamsLoading] = useState(true)
  const [teamsError, setTeamsError] = useState('')
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [search, setSearch] = useState('')
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    axios.get(`${API_BASE}/physical/teams`)
      .then(response => setTeams(response.data || []))
      .catch(requestError => setTeamsError(requestError.response?.data?.detail || 'Impossible de charger les équipes.'))
      .finally(() => setTeamsLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedTeam) return
    let active = true
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ limit: '500', team_name: selectedTeam.name })
      if (search.trim()) params.set('search', search.trim())
      setLoading(true)
      axios.get(`${API_BASE}/physical/players?${params}`)
        .then(response => { if (active) { setPlayers(response.data || []); setError('') } })
        .catch(requestError => { if (active) setError(requestError.response?.data?.detail || 'Impossible de charger les joueurs.') })
        .finally(() => { if (active) setLoading(false) })
    }, search ? 180 : 0)
    return () => { active = false; window.clearTimeout(timer) }
  }, [selectedTeam, search])

  const openTeam = team => { setSelectedTeam(team); setSearch(''); setPlayers([]); setError('') }
  const closeTeam = () => { setSelectedTeam(null); setSearch(''); setPlayers([]); setError('') }

  return <div className="physical-page physical-players-page">
    <Header eyebrow="PHYSICALDATA / JOUEURS" title={selectedTeam ? selectedTeam.name : 'Joueurs'} detail={selectedTeam ? 'Joueurs affiliés à cette équipe.' : 'Sélectionnez une équipe pour consulter les joueurs affiliés.'}>
      {selectedTeam && <button className="physical-back-button" type="button" onClick={closeTeam}><ArrowLeft size={16} aria-hidden="true" /> Toutes les équipes</button>}
    </Header>
    {selectedTeam ? <Panel kicker="Effectif de l’équipe" title="Joueurs affiliés" count={`${players.length} joueur(s)`}>
      <form className="physical-roster-search" role="search" onSubmit={event => event.preventDefault()}>
        <Search size={17} aria-hidden="true" />
        <input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Rechercher un joueur par nom" aria-label="Rechercher un joueur par nom" />
      </form>
      {loading ? <Empty>Recherche des joueurs…</Empty> : error ? <p className="physical-alert" role="alert">{error}</p> : <div className="physical-player-table"><div className="physical-table-head"><span>Joueur</span><span>Position</span><span>Équipe</span><span>Identifiant</span></div>{players.length ? players.map(player => <div className="physical-player-row" key={player.id}><strong>{player.display_name || `${player.first_name || ''} ${player.last_name || ''}`.trim() || 'Joueur sans nom'}</strong><span>{player.primary_position || player.secondary_position || '—'}</span><span>{selectedTeam.name}</span><small title={player.id}>{player.id}</small></div>) : <Empty>{search ? 'Aucun joueur ne correspond à cette recherche.' : 'Aucun joueur affilié à cette équipe.'}</Empty>}</div>}
    </Panel> : <Panel kicker="Équipes" title="Choisir une équipe" count={`${teams.length} équipe(s)`}>
      {teamsLoading ? <Empty>Chargement des équipes…</Empty> : teamsError ? <p className="physical-alert" role="alert">{teamsError}</p> : teams.length ? <div className="physical-team-card-grid">{teams.map(team => <button className="physical-team-card" type="button" key={team.name} onClick={() => openTeam(team)}>
        <span className="physical-team-card-icon"><UsersRound size={20} aria-hidden="true" /></span>
        <span className="physical-team-card-name">{team.name}</span>
        <span className="physical-team-card-meta">Sessions nommées « {team.name} - … »</span>
        <span className="physical-team-card-count"><strong>{Number(team.player_count || 0).toLocaleString('fr-FR')}</strong> joueurs</span>
      </button>)}</div> : <Empty>Aucune équipe disponible.</Empty>}
    </Panel>}
  </div>
}

export function Automation() {
  const weekdays = [['Lun', 0], ['Mar', 1], ['Mer', 2], ['Jeu', 3], ['Ven', 4], ['Sam', 5], ['Dim', 6]]
  const blank = { name: '', enabled: false, interval_minutes: 1440, window_start_utc: '00:00:00', window_end_utc: '23:59:59', weekdays: [0, 1, 2, 3, 4, 5, 6] }
  const [rules, setRules] = useState([]); const [form, setForm] = useState(blank); const [saving, setSaving] = useState(false); const [message, setMessage] = useState(''); const [runs, setRuns] = useState([]); const [editorOpen, setEditorOpen] = useState(false)
  const load = async () => { try { const [configResponse, overviewResponse] = await Promise.all([axios.get(`${API_BASE}/physical/scraping/automation/config`), axios.get(`${API_BASE}/physical/scraping/automation/overview`)]); setRules(configResponse.data || []); setRuns(overviewResponse.data?.runs || []) } catch (requestError) { setMessage(requestError.response?.data?.detail || requestError.message) } }
  useEffect(() => { load() }, [])
  const edit = rule => { setForm({ ...rule, weekdays: rule.weekdays || [0, 1, 2, 3, 4, 5, 6], window_start_utc: String(rule.window_start_utc).slice(0, 8), window_end_utc: String(rule.window_end_utc).slice(0, 8) }); setEditorOpen(true) }
  const openNew = () => { setForm({ ...blank }); setMessage(''); setEditorOpen(true) }
  const closeEditor = () => { if (!saving) { setEditorOpen(false); setForm({ ...blank }); setMessage('') } }
  const save = async event => { event.preventDefault(); setSaving(true); setMessage(''); try { const response = await axios.put(`${API_BASE}/physical/scraping/automation/config`, { ...form, interval_minutes: Number(form.interval_minutes), name: form.name.trim() }); setRules(current => [...current.filter(rule => rule.name !== response.data.name), response.data].sort((a, b) => a.name.localeCompare(b.name))); setEditorOpen(false); setForm({ ...blank }); setMessage('Automatisation rule saved.') } catch (requestError) { setMessage(requestError.response?.data?.detail || requestError.message) } finally { setSaving(false) } }
  const remove = async name => { try { await axios.delete(`${API_BASE}/physical/scraping/automation/config/${encodeURIComponent(name)}`); setRules(current => current.filter(rule => rule.name !== name)); setMessage('Automatisation rule deleted.') } catch (requestError) { setMessage(requestError.response?.data?.detail || requestError.message) } }
  return <div className="physical-page"><Header eyebrow="PHYSICALDATA / AUTOMATION" title="Automatisation" detail="Créez des règles d’importation indépendantes par jour, heures UTC et intervalle."><button className="physical-primary-button physical-automation-add" type="button" onClick={openNew}><Plus size={15} aria-hidden="true" /> Nouvelle règle</button></Header><div className="physical-automation-summary"><div><CalendarClock size={18} aria-hidden="true" /><span><strong>{rules.filter(rule => rule.enabled).length}</strong><small>règle(s) active(s)</small></span></div><div><span><strong>{runs.length}</strong><small>exécution(s) récente(s)</small></span></div><div><span><strong>{runs.filter(run => run.status === 'partial' || run.failed > 0).length}</strong><small>exécution(s) à vérifier</small></span></div></div><div className="physical-overview-grid"><Panel kicker="Règles" title="Importations planifiées" count={`${rules.length} rules`}><div className="physical-automation-rules">{rules.length ? rules.map(rule => <article className={`physical-automation-rule ${rule.enabled ? 'is-enabled' : ''}`} key={rule.name}><div className="physical-automation-rule-top"><span className="physical-automation-rule-status" /><div><strong>{rule.name}</strong><small>{rule.enabled ? 'Active' : 'En pause'}</small></div><button type="button" aria-label={`Edit ${rule.name}`} title="Modifier la règle" onClick={() => edit(rule)}><Pencil size={14} /></button><button type="button" aria-label={`Delete ${rule.name}`} title="Supprimer la règle" onClick={() => remove(rule.name)}><Trash2 size={14} /></button></div><div className="physical-automation-rule-meta"><span>{String(rule.window_start_utc).slice(0, 5)}–{String(rule.window_end_utc).slice(0, 5)} UTC</span><span>Toutes les {rule.interval_minutes} min</span></div><div className="physical-automation-days">{weekdays.map(([label, day]) => <i className={(rule.weekdays || []).includes(day) ? 'is-selected' : ''} key={day}>{label.slice(0, 1)}</i>)}</div></article>) : <Empty>Aucune règle d’automatisation configurée.</Empty>}</div></Panel><Panel kicker="Overview" title="Latest automation runs" count={`${runs.length} runs`}><div className="physical-automation-runs">{runs.length ? runs.map(run => <div className="physical-automation-run" key={run.id}><span className={`physical-run-status ${run.status}`}>{run.status}</span><div><strong>{run.display_name}</strong><small>{formatDate(run.started_at)}</small></div><em>{run.found} found · {run.inserted} new · {run.failed} failed</em></div>) : <Empty>No automated runs recorded yet.</Empty>}</div></Panel></div>{message && <div className="physical-form-message physical-automation-message">{message}</div>}{editorOpen && <><button className="offcanvas-backdrop" type="button" aria-label="Fermer automation editor" onClick={closeEditor} /><aside className="physical-automation-offcanvas" aria-label="Automatisation rule editor"><div className="offcanvas-header"><div><p className="eyebrow physical-eyebrow">RULE EDITOR</p><h3>{form.name ? `Edit ${form.name}` : 'New automation rule'}</h3></div><button className="offcanvas-close" type="button" onClick={closeEditor} aria-label="Fermer"><X size={22} /></button></div><form className="physical-config-form" onSubmit={save}><label>Rule name<input required value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} placeholder="matchday_morning" /></label><label className="physical-toggle"><input type="checkbox" checked={form.enabled} onChange={event => setForm({ ...form, enabled: event.target.checked })} /><span><strong>Enable rule</strong><small>Use the current UTC share date</small></span></label><label>Interval in minutes<input type="number" min="1" value={form.interval_minutes} onChange={event => setForm({ ...form, interval_minutes: event.target.value })} /></label><div className="physical-field-row"><label>Window start UTC<input type="time" step="1" value={String(form.window_start_utc).slice(0, 8)} onChange={event => setForm({ ...form, window_start_utc: event.target.value })} /></label><label>Window end UTC<input type="time" step="1" value={String(form.window_end_utc).slice(0, 8)} onChange={event => setForm({ ...form, window_end_utc: event.target.value })} /></label></div><fieldset><legend>Weekdays</legend><div className="physical-tabs">{weekdays.map(([label, day]) => <button key={day} type="button" className={form.weekdays.includes(day) ? 'is-active' : ''} onClick={() => setForm({ ...form, weekdays: form.weekdays.includes(day) ? form.weekdays.filter(value => value !== day) : [...form.weekdays, day].sort() })}>{label}</button>)}</div></fieldset><div className="physical-offcanvas-actions"><button className="physical-primary-button" disabled={saving || !form.weekdays.length}>{saving ? 'Saving...' : 'Save rule'}</button><button type="button" onClick={closeEditor}>Cancel</button></div></form></aside></>}</div>
}

export function Logs() {
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const load = () =>
    axios
      .get(`${API_BASE}/physical/logs?limit=100`)
      .then((response) => {
        const values = response.data || [];
        setRuns(values);
        if (!selected && values[0]) select(values[0]);
      })
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  const select = (run) => {
    setSelected({ run, logs: [] });
    setDetailLoading(true);
    axios
      .get(`${API_BASE}/physical/logs/${run.id}`)
      .then((response) => setSelected(response.data))
      .catch(() => {})
      .finally(() => setDetailLoading(false));
  };
  useEffect(() => {
    load();
  }, []);
  const visibleSteps =
    selected?.logs?.filter((log) =>
      [
        "run_started",
        "api_response",
        "activity_processing",
        "run_finished",
        "activity_failed",
      ].includes(log.step),
    ) || [];
  const activities =
    selected?.activities ||
    selected?.logs
      ?.filter(
        (log) =>
          log.activity_id &&
          [
            "activity_processing",
            "persistence",
            "data_presence",
            "activity_failed",
          ].includes(log.step),
      )
      .reduce((items, log) => {
        const current = items.find(
          (item) => item.activity_id === log.activity_id,
        );
        if (!current)
          items.push({
            ...log,
            status:
              log.step === "data_presence"
                ? "skipped"
                : log.step === "activity_failed"
                  ? "failed"
                  : log.step === "persistence"
                    ? log.details?.updated
                      ? "updated"
                      : "inserted"
                    : "processing",
            reason: log.message,
          });
        else if (
          ["data_presence", "persistence", "activity_failed"].includes(log.step)
        )
          Object.assign(current, {
            status:
              log.step === "data_presence"
                ? "skipped"
                : log.step === "activity_failed"
                  ? "failed"
                  : log.details?.updated
                    ? "updated"
                    : "inserted",
            reason: log.message,
          });
        return items;
      }, []) ||
    [];
  const parameterEntries = selected?.run?.request_payload
    ? Object.entries(selected.run.request_payload)
    : [];
  useEffect(() => {
    const rows = Array.from(
      document.querySelectorAll(
        ".physical-activity-list .physical-activity-item",
      ),
    );
    const activityList = document.querySelector(".physical-activity-list");
    const stepList = document.querySelector(".physical-step-list");
    if (activityList && stepList)
      stepList.parentElement.insertBefore(activityList, stepList);
    activities.forEach((activity, index) => {
      const row = rows[index];
      if (!row) return;
      const status = String(activity.status || "processing").toUpperCase();
      const reason =
        activity.reason || "Aucune raison complémentaire enregistrée";
      row.dataset.status = status.toLowerCase();
      row.title = reason;
      const existingBadge = row.querySelector(".physical-log-status-badge");
      if (existingBadge) existingBadge.remove();
      const badge = document.createElement("span");
      badge.className = "physical-log-status-badge";
      badge.textContent = status;
      row.prepend(badge);
      const detail = row.querySelector("small");
      if (detail) detail.textContent = `${status} · ${reason}`;
    });
  }, [activities]);
  return (
    <div className="physical-page">
      <Header
        eyebrow="PHYSICALDATA / ACTIVITY LOGS"
        title="Journaux d’activité"
        detail="Suivez chaque collecte manuelle par type, paramètres, cycle de vie et activités traitées."
      />
      <div className="physical-log-layout">
        <Panel
          kicker="Historique des exécutions"
          title="Exécutions de collecte"
          count={`${runs.length} runs`}
        >
          {loading ? (
            <Empty>Chargement des journaux d’activité...</Empty>
          ) : runs.length ? (
            <div className="physical-run-list">
              {runs.map((run) => (
                <button
                  className={`physical-run-row ${selected?.run?.id === run.id ? "is-selected" : ""}`}
                  key={run.id}
                  onClick={() => select(run)}
                >
                  <div>
                    <strong>{run.display_name}</strong>
                    <small>
                      {run.endpoint} · {formatDate(run.started_at)}
                    </small>
                  </div>
                  <span className={`physical-run-status ${run.status}`}>
                    {run.status}
                  </span>
                  <em>
                    {run.found} found · {run.inserted} new · {run.updated}{" "}
                    updated
                  </em>
                </button>
              ))}
            </div>
          ) : (
            <Empty>
              Aucune exécution de collecte n’a encore été enregistrée.
            </Empty>
          )}
        </Panel>
        <div className="physical-log-detail-column">
          <Panel
            kicker="Paramètres de collecte"
            title={selected?.run?.display_name || "Sélectionner une exécution"}
          >
            {!selected ? (
              <Empty>Sélectionner une exécution to inspect its details.</Empty>
            ) : (
              <div className="physical-parameter-list">
                {parameterEntries.map(([key, value]) => (
                  <div key={key}>
                    <b>{key}</b>
                    <strong>{String(value)}</strong>
                  </div>
                ))}
              </div>
            )}
          </Panel>
          {selected && (
            <Panel
              kicker="Détail de l’exécution"
              title="Lifecycle and activité(s)"
            >
              <div className="physical-run-detail">
                <div className="physical-run-facts">
                  <span>
                    <b>Status</b>
                    {selected.run.status}
                  </span>
                  <span>
                    <b>Started</b>
                    {formatDate(selected.run.started_at)}
                  </span>
                  <span>
                    <b>Finished</b>
                    {formatDate(selected.run.completed_at)}
                  </span>
                  <span>
                    <b>Activities found</b>
                    {selected.run.found}
                  </span>
                  <span>
                    <b>Inserted / updated</b>
                    {selected.run.inserted} / {selected.run.updated}
                  </span>
                  <span>
                    <b>Skipped / failed</b>
                    {selected.run.skipped} / {selected.run.failed}
                  </span>
                </div>
                {detailLoading ? (
                  <Empty>Chargement des étapes d’exécution...</Empty>
                ) : (
                  <>
                    <div className="physical-step-list">
                      {visibleSteps.map((log) => (
                        <div
                          className={`physical-step ${log.level === "ERROR" ? "is-error" : ""}`}
                          key={log.id}
                        >
                          <i />{" "}
                          <div>
                            <strong>
                              {log.step === "api_response"
                                ? "activité(s)_checked"
                                : log.step}
                            </strong>
                            <p>{log.message}</p>
                            <time>{formatDate(log.timestamp)}</time>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="physical-activity-list">
                      <div className="physical-activity-list-heading">
                        <b>Activities treated</b>
                        <span>{activities.length}</span>
                      </div>
                      {activities.length ? (
                        activities.map((activity) => (
                          <div
                            className="physical-activity-item"
                            key={activity.activity_id}
                          >
                            <strong>
                              {activity.activity_name || "Activité sans nom"}
                            </strong>
                            <small>{activity.activity_id}</small>
                          </div>
                        ))
                      ) : (
                        <Empty>No activity details recorded.</Empty>
                      )}
                    </div>
                  </>
                )}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
export function Settings({ catalog }) {
  const [names, setNames] = useState({});
  const [colors, setSquadColors] = useState(readSquadColors);
  const [saving, setSaving] = useState(null);
  const [message, setMessage] = useState("");
  const [section, setSection] = useState("squads");
  const [seasonForm, setSeasonForm] = useState({
    name: "",
    start_date: "",
    end_date: "",
  });
  const [editingSeason, setEditingSeason] = useState(null);
  const [seasonSaving, setSeasonSaving] = useState(false);
  useEffect(
    () =>
      setNames(
        Object.fromEntries(
          catalog.squads.map((squad) => [squad.id, squad.name || ""]),
        ),
      ),
    [catalog.squads],
  );
  const save = async (squad) => {
    setSaving(squad.id);
    setMessage("");
    try {
      await axios.put(`${API_BASE}/physical/squads/${squad.id}`, {
        name: names[squad.id].trim(),
      });
      localStorage.setItem("physical-squad-colors", JSON.stringify(colors));
      setMessage(`${squad.name || squad.external_id} updated.`);
      await catalog.reload();
    } catch (requestError) {
      setMessage(requestError.response?.data?.detail || requestError.message);
    } finally {
      setSaving(null);
    }
  };
  const changeColor = (squadId, color) =>
    setSquadColors((current) => {
      const next = { ...current, [squadId]: color };
      localStorage.setItem("physical-squad-colors", JSON.stringify(next));
      return next;
    });
  const saveSeason = async (event) => {
    event.preventDefault();
    setSeasonSaving(true);
    setMessage("");
    try {
      const method = editingSeason ? "put" : "post";
      const url = editingSeason
        ? `${API_BASE}/physical/seasons/${editingSeason}`
        : `${API_BASE}/physical/seasons`;
      await axios[method](url, seasonForm);
      setSeasonForm({ name: "", start_date: "", end_date: "" });
      setEditingSeason(null);
      setMessage("Saison enregistrée.");
      await catalog.reload();
    } catch (requestError) {
      setMessage(requestError.response?.data?.detail || requestError.message);
    } finally {
      setSeasonSaving(false);
    }
  };
  const editSeason = (season) => {
    setEditingSeason(season.id);
    setSeasonForm({
      name: season.name,
      start_date: String(season.start_date).slice(0, 10),
      end_date: String(season.end_date).slice(0, 10),
    });
  };
  return (
    <div className="physical-page">
      <Header
        eyebrow="PHYSICALDATA / SETTINGS"
        title="Paramètres"
        detail="Gérez les équipes, les couleurs du calendrier et les bornes de saison du 15 juin."
      />
      <div className="physical-settings-sections">
        <section
          className={`physical-settings-section ${section === "squads" ? "is-open" : ""}`}
        >
          <button
            type="button"
            className="physical-settings-toggle"
            onClick={() => setSection(section === "squads" ? "" : "squads")}
          >
            <span>
              <b>01</b>
              <strong>Équipes</strong>
              <small>Noms, identifiants et couleurs du calendrier</small>
            </span>
            <em>{section === "squads" ? "−" : "+"}</em>
          </button>
          {section === "squads" && (
            <Panel
              kicker="Catalogue des équipes"
              title="Nommer et colorer les équipes"
              count={`${catalog.squads.length} squads`}
            >
              {catalog.squads.length ? (
                <div className="physical-squad-settings">
                  {catalog.squads.map((squad, index) => (
                    <div className="physical-squad-setting" key={squad.id}>
                      <div className="physical-squad-identity">
                        <span
                          className="physical-squad-color-dot"
                          style={{
                            backgroundColor: colorForSquad(
                              squad,
                              index,
                              colors,
                            ),
                          }}
                        />
                        <div>
                          <strong>{squad.name || "Équipe sans nom"}</strong>
                          <small>
                            <b>STATSports ID</b> {squad.external_id}
                          </small>
                          <small>
                            <b>Identifiant base de données</b> {squad.id}
                          </small>
                        </div>
                      </div>
                      <input
                        value={names[squad.id] ?? ""}
                        onChange={(event) =>
                          setNames((current) => ({
                            ...current,
                            [squad.id]: event.target.value,
                          }))
                        }
                        placeholder="Nom affiché de l’équipe"
                        maxLength="255"
                      />
                      <label className="physical-color-control">
                        Couleur
                        <input
                          type="color"
                          value={colorForSquad(squad, index, colors)}
                          onChange={(event) =>
                            changeColor(squad.id, event.target.value)
                          }
                        />
                      </label>
                      <button
                        className="physical-save-icon"
                        aria-label={`Enregistrer le nom de ${squad.name || squad.external_id}`}
                        title="Enregistrer le nom de l’équipe"
                        disabled={
                          saving === squad.id || !names[squad.id]?.trim()
                        }
                        onClick={() => save(squad)}
                      >
                        <Save size={16} strokeWidth={2.5} aria-hidden="true" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty>Aucune équipe importée.</Empty>
              )}
            </Panel>
          )}
        </section>
        <section
          className={`physical-settings-section ${section === "seasons" ? "is-open" : ""}`}
        >
          <button
            type="button"
            className="physical-settings-toggle"
            onClick={() => setSection(section === "seasons" ? "" : "seasons")}
          >
            <span>
              <b>02</b>
              <strong>Saisons</strong>
              <small>Periods change every year on 15 June</small>
            </span>
            <em>{section === "seasons" ? "−" : "+"}</em>
          </button>
          {section === "seasons" && (
            <Panel
              kicker="Season catalog"
              title="Manage seasons"
              count={`${catalog.seasons.length} seasons`}
            >
              <form className="physical-season-form" onSubmit={saveSeason}>
                <label>
                  Name
                  <input
                    required
                    value={seasonForm.name}
                    onChange={(event) =>
                      setSeasonForm({ ...seasonForm, name: event.target.value })
                    }
                    placeholder="2027-2028"
                  />
                </label>
                <label>
                  Date de début
                  <input
                    required
                    type="date"
                    value={seasonForm.start_date}
                    onChange={(event) =>
                      setSeasonForm({
                        ...seasonForm,
                        start_date: event.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Date de fin
                  <input
                    required
                    type="date"
                    value={seasonForm.end_date}
                    onChange={(event) =>
                      setSeasonForm({
                        ...seasonForm,
                        end_date: event.target.value,
                      })
                    }
                  />
                </label>
                <button
                  className="physical-primary-button"
                  disabled={seasonSaving}
                >
                  {seasonSaving
                    ? "Saving..."
                    : editingSeason
                      ? "Update season"
                      : "Create season"}
                </button>
              </form>
              {editingSeason && (
                <button
                  className="physical-season-cancel"
                  type="button"
                  onClick={() => {
                    setEditingSeason(null);
                    setSeasonForm({ name: "", start_date: "", end_date: "" });
                  }}
                >
                  Cancel editing
                </button>
              )}
              <div className="physical-season-list">
                {catalog.seasons.map((season) => (
                  <div className="physical-season-row" key={season.id}>
                    <div>
                      <strong>{season.name}</strong>
                      <small>
                        {formatCalendarDate(season.start_date)} →{" "}
                        {formatCalendarDate(season.end_date)} ·{" "}
                        {season.activity_count} activité(s)
                      </small>
                    </div>
                    <button
                      className="physical-save-icon"
                      type="button"
                      title={`Edit ${season.name}`}
                      aria-label={`Edit ${season.name}`}
                      onClick={() => editSeason(season)}
                    >
                      ✎
                    </button>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </section>
      </div>
      {message && <p className="physical-form-message">{message}</p>}
    </div>
  );
}

