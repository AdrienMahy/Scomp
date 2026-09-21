import { useState, useEffect } from 'react'
import axios from 'axios'
import { Card, Badge, ErrorAlert, SuccessAlert } from '../components'

const API_BASE = '/api'

export default function ScrapingPage({ scope }) {
  const [rounds, setRounds] = useState([])
  const [selectedRounds, setSelectedRounds] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [queuedTasks, setQueuedTasks] = useState([])

  // Fetch available rounds
  useEffect(() => {
    fetchRounds()
    setSelectedRounds([])
  }, [scope?.competitionId, scope?.seasonId])

  const fetchRounds = async () => {
    try {
      const res = await axios.get(`${API_BASE}/games/rounds`, {
        params: { competition_id: scope?.competitionId, season_id: scope?.seasonId },
      })
      setRounds(res.data.rounds)
    } catch (err) {
      setError('Failed to load rounds')
    }
  }

  const toggleRound = (round) => {
    if (selectedRounds.includes(round)) {
      setSelectedRounds(selectedRounds.filter(r => r !== round))
    } else {
      setSelectedRounds([...selectedRounds, round])
    }
  }

  const handleScrape = async (type) => {
    if (!scope) {
      setError('Select a competition and season in Active Season first.')
      return
    }
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const roundsToScrape = type === 'rounds' ? selectedRounds : null

      if (type === 'rounds') {
        const responses = await Promise.all(roundsToScrape.map(round => axios.post(`${API_BASE}/games/scrape-unified`, {
          competition_id: scope.competitionId,
          season_id: scope.seasonId,
          round,
        })))
        setQueuedTasks(responses.map(response => response.data))
        setSuccess(`${roundsToScrape.length} round(s) queued.`)
      } else if (type === 'players') {
        const response = await axios.post(`${API_BASE}/players/scrape-players`, null, {
          params: { competition_id: scope.competitionId, season_id: scope.seasonId },
        })
        setQueuedTasks([response.data])
        setSuccess('Player enrichment queued.')
      }
      setSelectedRounds([])
    } catch (err) {
      setError(`Error: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="scraping-page">
      <div className="scraping-hero">
        <div><p className="eyebrow">WORKSPACE / SCRAPING</p><h1>Pipeline control</h1><p>Run a workflow against the active competition and season.</p></div>
        <div className="scraping-context"><span className="status-dot" /><strong>{scope?.competitionName || 'No competition'}</strong><span>{scope?.seasonName || 'Select a season in the sidebar'}</span></div>
      </div>

      {/* Alerts */}
      <div className="space-y-3">
        {error && <ErrorAlert message={error} />}
        {success && <SuccessAlert message={success} />}
      </div>

      {/* Control Panel */}
      <div className="scraping-workspaces">
        <Card title="Scrape rounds" subtitle={`${selectedRounds.length} round(s) selected`}>
          <div className="round-grid">
          {rounds.map(round => (
            <button
              key={round}
              onClick={() => toggleRound(round)}
                className={`round-chip ${
                selectedRounds.includes(round)
                  ? 'bg-primary-500 text-white'
                  : 'bg-light-200 dark:bg-dark-700 hover:bg-light-300 dark:hover:bg-dark-600'
              }`}
            >
              J{round}
            </button>
          ))}
          </div>
          <button className="workspace-action primary" onClick={() => selectedRounds.length > 0 ? handleScrape('rounds') : null} disabled={loading || selectedRounds.length === 0 || !scope}>
            <span>↯</span><div><strong>Process selected rounds</strong><small>{scope ? 'Parse, persist and enrich the selected matchdays' : 'Select a competition and season first'}</small></div><b>→</b>
          </button>
        </Card>

        <Card title="Player enrichment" subtitle="Complete player profiles for the active season">
          <div className="enrichment-workspace"><span className="workspace-symbol">✦</span><p>Enrich only the players linked to games in the active competition and season.</p></div>
          <button className="workspace-action" onClick={() => handleScrape('players')} disabled={loading || !scope}>
            <span>✦</span><div><strong>Enrich players</strong><small>{scope ? 'Queue the player enrichment task' : 'Select a competition and season first'}</small></div><b>→</b>
          </button>
        </Card>
      </div>

      {queuedTasks.length > 0 && <Card title="Queued executions" subtitle="Follow progress in Activity logs">
        <div className="queued-task-list">{queuedTasks.map(task => <div className="queued-task" key={task.task_id}><span className="status-dot" /><div><strong>{task.workflow}</strong><small>{task.task_id}</small></div><Badge variant="warning">Queued</Badge></div>)}</div>
      </Card>}

    </div>
  )
}
