import { useState, useEffect } from 'react'
import axios from 'axios'
import { Card, Badge, ErrorAlert, SuccessAlert } from '../../components'
import { API_BASE } from '../api'

const PARSER_OPTIONS = [
  { id: 'lineups', label: 'Lineups', description: 'Teams and players must already exist.' },
  { id: 'periods', label: 'Periods and score evolution', description: 'Match periods and score timeline.' },
  { id: 'substitutions', label: 'Substitutions', description: 'Uses players and teams already in the database.' },
  { id: 'team_distance', label: 'Team distances', description: 'Team distance metrics and intervals.' },
  { id: 'player_distance', label: 'Player distances', description: 'Reads metadata only if existing lineups cannot assign teams.' },
  { id: 'rgd', label: 'RGD events and phases', description: 'If fitness runs exist, select Fitness too to refresh their references.' },
  { id: 'goals', label: 'Goals only', description: 'Downloads RGD and replaces only this match’s goals.' },
  { id: 'fitness', label: 'Fitness runs', description: 'Fitness runs and their summaries.' },
]

const STANDARD_PARSER_IDS = PARSER_OPTIONS
  .filter(parser => parser.id !== 'goals')
  .map(parser => parser.id)

export default function ScrapingPage({ scope }) {
  const [rounds, setRounds] = useState([])
  const [selectedRounds, setSelectedRounds] = useState([])
  const [selectedParsers, setSelectedParsers] = useState(
    STANDARD_PARSER_IDS
  )
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

  const toggleParser = (parserId) => {
    setSelectedParsers(current => {
      if (parserId === 'goals') {
        return current.includes('goals') ? [] : ['goals']
      }
      const compatible = current.filter(id => id !== 'goals')
      return compatible.includes(parserId)
        ? compatible.filter(id => id !== parserId)
        : [...compatible, parserId]
    })
  }

  const handleScrape = async (type) => {
    if (!scope) {
      setError('Select a competition and season in Active Season first.')
      return
    }
    if (type === 'rounds' && selectedParsers.length === 0) {
      setError('Select at least one parser.')
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
          parsers: selectedParsers,
        })))
        setQueuedTasks(responses.map(response => response.data))
        setSuccess(
          `${roundsToScrape.length} round(s) queued with ${selectedParsers.length} parser(s).`
        )
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
        <Card
          title="Scrape rounds"
          subtitle={`${selectedRounds.length} round(s), ${selectedParsers.length} parser(s) selected`}
        >
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
          <section className="parser-selection" aria-labelledby="parser-selection-title">
            <div className="parser-selection-heading">
              <div>
                <h2 id="parser-selection-title">Parsers to run</h2>
                <p>Only selected parsers and their required files will be processed. Goals only is an exclusive refresh.</p>
              </div>
              <div className="parser-selection-actions">
                <button
                  type="button"
                  onClick={() => setSelectedParsers(STANDARD_PARSER_IDS)}
                  disabled={loading}
                >
                  Select all standard parsers
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedParsers([])}
                  disabled={loading}
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="parser-grid">
              {PARSER_OPTIONS.map(parser => (
                <label
                  className={`parser-option ${
                    selectedParsers.includes(parser.id) ? 'is-selected' : ''
                  }`}
                  key={parser.id}
                >
                  <input
                    type="checkbox"
                    checked={selectedParsers.includes(parser.id)}
                    onChange={() => toggleParser(parser.id)}
                    disabled={loading}
                  />
                  <span>
                    <strong>{parser.label}</strong>
                    <small>{parser.description}</small>
                  </span>
                </label>
              ))}
            </div>
          </section>
          <button className="workspace-action primary" onClick={() => selectedRounds.length > 0 ? handleScrape('rounds') : null} disabled={loading || selectedRounds.length === 0 || selectedParsers.length === 0 || !scope}>
            <span>↯</span><div><strong>Process selected rounds</strong><small>{scope ? 'Download required files and run selected parsers' : 'Select a competition and season first'}</small></div><b>→</b>
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
        <div className="queued-task-list">{queuedTasks.map(task => <div className="queued-task" key={task.task_id}><span className="status-dot" /><div><strong>{task.workflow}</strong>{Array.isArray(task.parsers) && <small>Parsers: {task.parsers.join(', ')}</small>}<small>{task.task_id}</small></div><Badge variant="warning">Queued</Badge></div>)}</div>
      </Card>}

    </div>
  )
}
