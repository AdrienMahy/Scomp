import { useEffect, useState } from 'react'
import axios from 'axios'
import { API_BASE } from '../api'
import { usePhysicalCatalog } from '../components/PhysicalDataViews'

const DEFAULT_TEAM_COLORS = ['#55d6c0', '#f2b84b', '#e86a92', '#8da7ff', '#c38cff', '#f28f5b', '#78d46d']

function readTeamColors() {
  try {
    return JSON.parse(localStorage.getItem('physical-squad-colors') || '{}')
  } catch {
    return {}
  }
}

function teamKey(name) {
  return name.trim().toLocaleLowerCase()
}

function Panel({ kicker, title, count, children }) {
  return <section className="physical-panel"><div className="physical-panel-heading"><div><span className="physical-kicker">{kicker}</span><h2>{title}</h2></div>{count !== undefined && <span className="physical-count">{count}</span>}</div>{children}</section>
}

function Empty({ children }) {
  return <div className="physical-empty">{children}</div>
}

function formatSeasonDate(value) {
  if (!value) return '—'
  return new Date(`${String(value).slice(0, 10)}T00:00:00Z`).toLocaleDateString('fr-FR', { dateStyle: 'long', timeZone: 'UTC' })
}

export default function SettingsPage() {
  const catalog = usePhysicalCatalog()
  const [teams, setTeams] = useState([])
  const [teamsLoading, setTeamsLoading] = useState(true)
  const [teamsError, setTeamsError] = useState('')
  const [colors, setColors] = useState(readTeamColors)
  const [section, setSection] = useState('teams')
  const [seasonForm, setSeasonForm] = useState({ name: '', start_date: '', end_date: '' })
  const [editingSeason, setEditingSeason] = useState(null)
  const [seasonSaving, setSeasonSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    axios.get(`${API_BASE}/physical/teams`)
      .then(response => setTeams(response.data || []))
      .catch(requestError => setTeamsError(requestError.response?.data?.detail || 'Impossible de charger les équipes.'))
      .finally(() => setTeamsLoading(false))
  }, [])

  const updateTeamColor = (team, color) => setColors(current => {
    const next = { ...current, [teamKey(team.name)]: color }
    localStorage.setItem('physical-squad-colors', JSON.stringify(next))
    return next
  })

  const saveSeason = async event => {
    event.preventDefault()
    setSeasonSaving(true)
    setMessage('')
    try {
      const method = editingSeason ? 'put' : 'post'
      const url = editingSeason ? `${API_BASE}/physical/seasons/${editingSeason}` : `${API_BASE}/physical/seasons`
      await axios[method](url, seasonForm)
      setSeasonForm({ name: '', start_date: '', end_date: '' })
      setEditingSeason(null)
      setMessage('Saison enregistrée.')
      await catalog.reload()
    } catch (requestError) {
      setMessage(requestError.response?.data?.detail || requestError.message)
    } finally {
      setSeasonSaving(false)
    }
  }

  const editSeason = season => {
    setEditingSeason(season.id)
    setSeasonForm({ name: season.name, start_date: String(season.start_date).slice(0, 10), end_date: String(season.end_date).slice(0, 10) })
  }

  return <div className="physical-page">
    <header className="physical-hero">
      <div><p className="eyebrow physical-eyebrow">PHYSICALDATA / PARAMÈTRES</p><h1>Paramètres</h1><p>Gérez les couleurs des équipes nommées dans les sessions et les bornes de saison.</p></div>
    </header>
    <div className="physical-settings-sections">
      <section className={`physical-settings-section ${section === 'teams' ? 'is-open' : ''}`}>
        <button type="button" className="physical-settings-toggle" onClick={() => setSection(section === 'teams' ? '' : 'teams')}>
          <span><b>01</b><strong>Équipes</strong><small>Noms des sessions et couleurs du calendrier</small></span><em>{section === 'teams' ? '−' : '+'}</em>
        </button>
        {section === 'teams' && <Panel kicker="Équipes des sessions" title="Couleurs du calendrier" count={`${teams.length} équipes`}>
          {teamsLoading ? <Empty>Chargement des équipes…</Empty> : teamsError ? <p className="physical-alert" role="alert">{teamsError}</p> : teams.length ? <div className="physical-squad-settings">{teams.map((team, index) => {
            const key = teamKey(team.name)
            const color = colors[key] || DEFAULT_TEAM_COLORS[index % DEFAULT_TEAM_COLORS.length]
            return <div className="physical-squad-setting" key={key}>
              <div className="physical-squad-identity"><span className="physical-squad-color-dot" style={{ backgroundColor: color }} /><div><strong>{team.name}</strong><small>{team.player_count} joueur(s)</small></div></div>
              <label className="physical-color-control">Couleur<input type="color" value={color} aria-label={`Couleur de ${team.name}`} onChange={event => updateTeamColor(team, event.target.value)} /></label>
            </div>
          })}</div> : <Empty>Aucune équipe nommée dans les sessions.</Empty>}
        </Panel>}
      </section>
      <section className={`physical-settings-section ${section === 'seasons' ? 'is-open' : ''}`}>
        <button type="button" className="physical-settings-toggle" onClick={() => setSection(section === 'seasons' ? '' : 'seasons')}>
          <span><b>02</b><strong>Saisons</strong><small>Bornes de saison à partir du 15 juin</small></span><em>{section === 'seasons' ? '−' : '+'}</em>
        </button>
        {section === 'seasons' && <Panel kicker="Calendrier des saisons" title="Gérer les saisons" count={`${catalog.seasons.length} saisons`}>
          <form className="physical-season-form" onSubmit={saveSeason}>
            <label>Nom<input required value={seasonForm.name} onChange={event => setSeasonForm({ ...seasonForm, name: event.target.value })} placeholder="2027-2028" /></label>
            <label>Date de début<input required type="date" value={seasonForm.start_date} onChange={event => setSeasonForm({ ...seasonForm, start_date: event.target.value })} /></label>
            <label>Date de fin<input required type="date" value={seasonForm.end_date} onChange={event => setSeasonForm({ ...seasonForm, end_date: event.target.value })} /></label>
            <button className="physical-primary-button" disabled={seasonSaving}>{seasonSaving ? 'Enregistrement…' : editingSeason ? 'Modifier la saison' : 'Créer la saison'}</button>
          </form>
          {editingSeason && <button className="physical-season-cancel" type="button" onClick={() => { setEditingSeason(null); setSeasonForm({ name: '', start_date: '', end_date: '' }) }}>Annuler la modification</button>}
          <div className="physical-season-list">{catalog.seasons.map(season => <div className="physical-season-row" key={season.id}>
            <div><strong>{season.name}</strong><small>{formatSeasonDate(season.start_date)} → {formatSeasonDate(season.end_date)} · {season.activity_count} activité(s)</small></div>
            <button className="physical-save-icon" type="button" title={`Modifier ${season.name}`} aria-label={`Modifier ${season.name}`} onClick={() => editSeason(season)}>✎</button>
          </div>)}</div>
        </Panel>}
      </section>
    </div>
    {message && <p className="physical-form-message" role="status">{message}</p>}
  </div>
}