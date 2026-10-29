import { useEffect, useState } from 'react'
import axios from 'axios'
import { CalendarClock, ChevronRight, Play, Sparkles } from 'lucide-react'
import { Card, Loading, ErrorAlert } from '../../components'
import { API_BASE } from '../api'

function formatTaskDate(task) {
  const timestamp = task.started_at || task.created_at
  if (!timestamp) return 'Date indisponible'
  const normalizedTimestamp = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(timestamp) ? timestamp : `${timestamp}Z`
  const date = new Date(normalizedTimestamp)
  if (Number.isNaN(date.getTime())) return 'Date indisponible'
  return date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function formatProcessedCount(value) {
  const count = Number(value) || 0
  const plural = count === 1 ? '' : 's'
  return `${count} élément${plural} traité${plural}`
}

function Metric({ label, value, detail, accent = 'lime' }) {
  return (
    <div className={`overview-metric metric-${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  )
}

export default function OverviewPage({ onNavigate }) {
  const [competitions, setCompetitions] = useState([])
  const [tasks, setTasks] = useState([])
  const [automation, setAutomation] = useState(null)
  const [automationConfigurations, setAutomationConfigurations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true

    async function loadOverview() {
      try {
        const [competitionsResponse, tasksResponse, automationResponse, configurationsResponse] = await Promise.all([
          axios.get(`${API_BASE}/competitions`),
          axios.get(`${API_BASE}/games/tasks/list?limit=10`),
          axios.get(`${API_BASE}/automation/status`),
          axios.get(`${API_BASE}/automation/configurations`).catch(() => ({ data: [] })),
        ])
        if (!active) return
        setCompetitions(competitionsResponse.data || [])
        setTasks(tasksResponse.data?.tasks || [])
        setAutomation(automationResponse.data || null)
        setAutomationConfigurations(configurationsResponse.data || [])
      } catch (requestError) {
        if (active) setError(requestError.response?.data?.detail || requestError.message)
      } finally {
        if (active) setLoading(false)
      }
    }

    loadOverview()
    return () => { active = false }
  }, [])

  if (loading) return <Loading />
  const competitionNames = new Map(competitions
    .filter(competition => competition.name !== `Competition ${competition.id}`)
    .map(competition => [String(competition.id), competition.name]))
  const configuredCompetitionNames = new Map(automationConfigurations
    .map(configuration => [String(configuration.competition_id), configuration.competition_name]))

  return (
    <div className="overview-page">
      <div className="overview-hero dashboard-hero">
        <div>
          <p className="eyebrow">TACTICALDATA / SPORTSDYNAMICS</p>
          <h1>Tableau de bord SportsDynamics</h1>
          <p>Pilotez le pipeline de données de la compétition depuis un espace unique.</p>
        </div>
      </div>

      {error && <ErrorAlert message={`Données de synthèse indisponibles : ${error}`} />}

      <div className="overview-metrics dashboard-metrics">
        <Metric label="Compétitions" value={competitions.length} detail="configurées en base" />
        <Metric label="Tâches actives" value={tasks.filter(task => task.status === 'running').length} detail="en cours de traitement" accent="blue" />
        <Metric label="Matchs suivis" value={automation?.total_games_in_db ?? '—'} detail="toutes saisons confondues" accent="gold" />
        <Metric label="Automatisation" value={automation?.is_enabled ? 'ACTIVE' : 'INACTIVE'} detail={automation?.scrape_interval_minutes ? `toutes les ${automation.scrape_interval_minutes} min` : 'mode manuel'} accent={automation?.is_enabled ? 'lime' : 'red'} />
      </div>

      <div className="overview-grid dashboard-overview-grid">
        <Card title="Actions rapides" subtitle="Lancez un workflow depuis la vue d’ensemble">
          <div className="quick-actions">
            <button onClick={() => onNavigate('scraping')}><span><Play size={18} aria-hidden="true" /></span><div><strong>Lancer une collecte</strong><small>Initialiser une saison ou traiter une journée</small></div><ChevronRight size={17} aria-hidden="true" /></button>
            <button onClick={() => onNavigate('enrichment')}><span><Sparkles size={18} aria-hidden="true" /></span><div><strong>Enrichir les joueurs</strong><small>Compléter les profils depuis les compositions</small></div><ChevronRight size={17} aria-hidden="true" /></button>
            <button onClick={() => onNavigate('automation')}><span><CalendarClock size={18} aria-hidden="true" /></span><div><strong>Vérifier l’automatisation</strong><small>Contrôler la configuration des tâches autonomes</small></div><ChevronRight size={17} aria-hidden="true" /></button>
          </div>
        </Card>

        <Card title="Activité récente" subtitle="Dernières tâches d’orchestration">
          <div className="activity-list">
            {tasks.length === 0 && <p className="empty-state">Aucune tâche enregistrée pour le moment.</p>}
            {tasks.slice(0, 5).map(task => (
              <div className="activity-row" key={task.id}>
                <span className={`activity-dot activity-${task.status}`} />
                <div>
                  <strong>{task.provider || 'SportsDynamics'} scrape</strong>
                  <small>{configuredCompetitionNames.get(String(task.competition_id)) || competitionNames.get(String(task.competition_id)) || 'Compétition inconnue'} · {formatTaskDate(task)} · {formatProcessedCount(task.processed_items)}</small>
                </div>
                <span className="activity-status">{task.status}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
