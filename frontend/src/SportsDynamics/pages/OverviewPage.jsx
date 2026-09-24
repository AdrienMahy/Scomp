import { useEffect, useState } from 'react'
import axios from 'axios'
import { Card, Loading, ErrorAlert, Badge } from '../../components'
import { API_BASE } from '../api'

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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true

    async function loadOverview() {
      try {
        const [competitionsResponse, tasksResponse, automationResponse] = await Promise.all([
          axios.get(`${API_BASE}/competitions`),
          axios.get(`${API_BASE}/games/tasks/list?limit=10`),
          axios.get(`${API_BASE}/automation/status`),
        ])
        if (!active) return
        setCompetitions(competitionsResponse.data || [])
        setTasks(tasksResponse.data?.tasks || [])
        setAutomation(automationResponse.data || null)
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

  return (
    <div className="overview-page">
      <div className="overview-hero">
        <div>
          <p className="eyebrow">CONTROL ROOM / OVERVIEW</p>
          <h1>Good morning, operator.</h1>
          <p>Keep the competition data pipeline moving from one quiet workspace.</p>
        </div>
        <div className="hero-signal"><span className="status-dot" /> All systems nominal</div>
      </div>

      {error && <ErrorAlert message={`Overview data unavailable: ${error}`} />}

      <div className="overview-metrics">
        <Metric label="Competitions" value={competitions.length} detail="configured in database" />
        <Metric label="Active tasks" value={tasks.filter(task => task.status === 'running').length} detail="currently processing" accent="blue" />
        <Metric label="Tracked games" value={automation?.total_games_in_db ?? '—'} detail="across all seasons" accent="gold" />
        <Metric label="Automation" value={automation?.is_enabled ? 'ON' : 'OFF'} detail={automation?.scrape_interval_minutes ? `every ${automation.scrape_interval_minutes} min` : 'manual mode'} accent={automation?.is_enabled ? 'lime' : 'red'} />
      </div>

      <div className="overview-grid">
        <Card title="Quick actions" subtitle="Start a workflow without leaving the overview">
          <div className="quick-actions">
            <button onClick={() => onNavigate('scraping')}><span>↯</span><div><strong>Run a scrape</strong><small>Initialize a season or process a round</small></div><b>→</b></button>
            <button onClick={() => onNavigate('enrichment')}><span>✦</span><div><strong>Enrich players</strong><small>Complete profiles from processed lineups</small></div><b>→</b></button>
            <button onClick={() => onNavigate('automation')}><span>◌</span><div><strong>Review automation</strong><small>Inspect autonomous task configuration</small></div><b>→</b></button>
          </div>
        </Card>

        <Card title="Competitions" subtitle="Current database scope">
          <div className="competition-list">
            {competitions.length === 0 && <p className="empty-state">No competitions registered.</p>}
            {competitions.map(competition => (
              <div className="competition-row" key={competition.id}>
                <span className="competition-badge">{competition.name?.slice(0, 1) || 'C'}</span>
                <div><strong>{competition.name}</strong><small>{competition.provider || 'SportsDynamics'}</small></div>
                <Badge variant="success">Ready</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Recent activity" subtitle="Latest orchestration tasks">
        <div className="activity-list">
          {tasks.length === 0 && <p className="empty-state">No tasks have been recorded yet.</p>}
          {tasks.slice(0, 5).map(task => (
            <div className="activity-row" key={task.id}>
              <span className={`activity-dot activity-${task.status}`} />
              <div><strong>{task.provider || 'SportsDynamics'} scrape</strong><small>{task.competition_id || 'No competition'} · {task.processed_items || 0} processed</small></div>
              <span className="activity-status">{task.status}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
