import { useState, useEffect } from 'react'
import axios from 'axios'
import { Card, Loading, ErrorAlert, Select } from '../components'
import GameMatchCard from '../components/GameMatchCard'

const API_BASE = '/api'

export default function GameListPage({ scope }) {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filterMode, setFilterMode] = useState('round') // 'round' or 'team'
  const [selectedFilter, setSelectedFilter] = useState('1')
  const [rounds, setRounds] = useState([])
  const [teams, setTeams] = useState([])
  const [selectedGame, setSelectedGame] = useState(null)
  const [scrapeLoading, setScrapeLoading] = useState(false)
  const [scrapeMessage, setScrapeMessage] = useState(null)
  const [rawStats, setRawStats] = useState(null)

  // Load available rounds and teams
  useEffect(() => {
    fetchRounds()
  }, [scope?.competitionId, scope?.seasonId])

  useEffect(() => {
    fetchTeams()
  }, [scope?.competitionId, scope?.seasonId])

  // Load games when filter changes
  useEffect(() => {
    fetchGames()
  }, [filterMode, selectedFilter, scope?.competitionId, scope?.seasonId])

  const fetchRounds = async () => {
    try {
      const res = await axios.get(`${API_BASE}/games/rounds`)
      setRounds(res.data.rounds || [])
    } catch (err) {
      console.error('Failed to load rounds', err)
    }
  }

  const fetchTeams = async () => {
    try {
      const res = await axios.get(`${API_BASE}/teams`, {
        params: {
          limit: 500,
          competition_id: scope?.competitionId,
          season_id: scope?.seasonId,
        },
      })
      const options = (res.data || [])
        .map(team => ({ label: team.name, value: team.id }))
        .sort((left, right) => {
          const leftPriority = /stade de reims|reims/i.test(left.label) ? 0 : 1
          const rightPriority = /stade de reims|reims/i.test(right.label) ? 0 : 1
          return leftPriority - rightPriority || left.label.localeCompare(right.label)
        })
      setTeams(options)
      setSelectedFilter(current => options.some(option => option.value === current) ? current : (options[0]?.value || ''))
    } catch (err) {
      console.error('Failed to load teams', err)
    }
  }

  const fetchGames = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = filterMode === 'round'
        ? { round_name: selectedFilter, competition_id: scope?.competitionId, season_id: scope?.seasonId }
        : { team_id: selectedFilter, competition_id: scope?.competitionId, season_id: scope?.seasonId }

      const res = await axios.get(`${API_BASE}/games`, { params })
      const sortedGames = (res.data || []).sort((left, right) => {
        const leftPriority = /stade de reims|reims/i.test(left.name || '') ? 0 : 1
        const rightPriority = /stade de reims|reims/i.test(right.name || '') ? 0 : 1
        return leftPriority - rightPriority
      })
      setGames(sortedGames)
    } catch (err) {
      setError('Failed to load games')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const scrapeSelectedGame = async () => {
    if (!selectedGame) return
    setScrapeLoading(true)
    setScrapeMessage(null)
    try {
      const response = await axios.post(`${API_BASE}/games/${selectedGame.id}/scrape-game`)
      setScrapeMessage({ type: 'success', text: `Queued · task ${response.data.task_id?.slice(0, 8) || 'created'}` })
    } catch (err) {
      setScrapeMessage({ type: 'error', text: err.response?.data?.detail || err.message })
    } finally {
      setScrapeLoading(false)
    }
  }

  useEffect(() => {
    if (!selectedGame) {
      setRawStats(null)
      return
    }
    axios.get(`${API_BASE}/games/${selectedGame.id}/raw-stats`)
      .then(response => setRawStats(response.data))
      .catch(() => setRawStats(null))
  }, [selectedGame?.id])

  return (
    <div className="matches-page">
      {/* Header */}
      <div className="matches-header">
        <p className="eyebrow">WORKSPACE / MATCHES</p>
        <h2 className="matches-title">Match registry</h2>
        <p className="matches-intro">Browse processed fixtures and launch a focused reprocessing task.</p>
      </div>

      {/* Filters */}
      <Card title="Registry filters" subtitle="Narrow the competition view">
        <div className="matches-filter-grid">
          {/* Filter Mode */}
          <div className="flex gap-2">
            <button
              onClick={() => { setFilterMode('round'); setSelectedFilter(rounds[0] || '1') }}
                className={`filter-toggle ${
                filterMode === 'round'
                  ? 'bg-primary-500 text-white'
                  : 'bg-light-200 dark:bg-dark-700 hover:bg-light-300'
              }`}
            >
              By Round
            </button>
            <button
              onClick={() => { setFilterMode('team'); setSelectedFilter(teams[0]?.value || '') }}
                className={`filter-toggle ${
                filterMode === 'team'
                  ? 'bg-primary-500 text-white'
                  : 'bg-light-200 dark:bg-dark-700 hover:bg-light-300'
              }`}
            >
              By Team
            </button>
          </div>

          {/* Selection Dropdown */}
          {filterMode === 'round' && (
            <Select
              label="Journée"
              options={rounds.map(r => ({ label: `J${r}`, value: r }))}
              value={selectedFilter}
              onChange={(e) => setSelectedFilter(e.target.value)}
            />
          )}
          {filterMode === 'team' && (
            <Select
              label="Team"
              options={teams}
              value={selectedFilter}
              onChange={(e) => setSelectedFilter(e.target.value)}
            />
          )}
        </div>
      </Card>

      {/* Error Alert */}
      {error && <ErrorAlert message={error} />}

      {/* Games List */}
      {loading && <Loading />}
      {!loading && games.length > 0 && (
        <div>
          <div>
            <span className="matches-list-label">{games.length} fixture{games.length > 1 ? 's' : ''}</span>
          </div>
          <div className="space-y-4">
            {games.map(game => (
              <GameMatchCard
                key={game.id}
                game={game}
                onClick={() => setSelectedGame(game)}
              />
            ))}
          </div>
        </div>
      )}

      {!loading && games.length === 0 && (
        <Card title="No Games Found">
          <p className="text-neutral-600 dark:text-neutral-400">No matches available for the selected filter.</p>
        </Card>
      )}

      {selectedGame && (
        <>
          <button className="offcanvas-backdrop" onClick={() => setSelectedGame(null)} aria-label="Close match details" />
          <aside className="match-offcanvas" aria-label="Match details">
            <div className="offcanvas-header">
              <div><p className="eyebrow">MATCH / DETAILS</p><h3>Match information</h3></div>
              <button className="offcanvas-close" onClick={() => setSelectedGame(null)} aria-label="Close">×</button>
            </div>
            <div className="offcanvas-match-name">{selectedGame.name}</div>
            <div className="offcanvas-score"><strong>{selectedGame.home_score ?? '—'}</strong><span>:</span><strong>{selectedGame.away_score ?? '—'}</strong></div>
            <div className="offcanvas-status-row"><span>Provider status</span><strong>{selectedGame.status?.rgd_status || selectedGame.status?.ugd_status || (selectedGame.data_processed ? 'PROCESSED' : 'PENDING')}</strong></div>
            <button className="offcanvas-scrape-button" onClick={scrapeSelectedGame} disabled={scrapeLoading}>
              {scrapeLoading ? 'Queueing scrape...' : '↻ Reprocess this match'}
            </button>
            {scrapeMessage && <div className={`offcanvas-task-message ${scrapeMessage.type}`}>{scrapeMessage.text}</div>}
            <a className="offcanvas-download-button" href={`${API_BASE}/games/${selectedGame.id}/download-json`} download>
              ↓ Download fresh JSON files
            </a>
            <div className="offcanvas-section"><span className="offcanvas-label">Identifiers</span><dl>
              <dt>Game ID</dt><dd>{selectedGame.id}</dd>
              <dt>Home team ID</dt><dd>{selectedGame.home_team?.id || '—'}</dd>
              <dt>Away team ID</dt><dd>{selectedGame.away_team?.id || '—'}</dd>
            </dl></div>
            <div className="offcanvas-section"><span className="offcanvas-label">Match timing</span><dl>
              <dt>Match date</dt><dd>{selectedGame.starts_at ? new Date(selectedGame.starts_at).toLocaleString('fr-FR') : '—'}</dd>
              <dt>Last scrape</dt><dd>{selectedGame.updated_at ? new Date(selectedGame.updated_at).toLocaleString('fr-FR') : '—'}</dd>
              <dt>Created in database</dt><dd>{selectedGame.created_at ? new Date(selectedGame.created_at).toLocaleString('fr-FR') : '—'}</dd>
            </dl></div>
            <div className="offcanvas-section"><span className="offcanvas-label">Data availability</span><p className="offcanvas-help">Local availability reflects whether this match was successfully processed and stored.</p><div className="offcanvas-chips"><span className={selectedGame.data_processed ? 'is-positive' : selectedGame.status?.available ? 'is-positive' : 'is-negative'}><i />{selectedGame.data_processed ? 'Local data available' : selectedGame.status?.available ? 'Provider available' : 'Provider unavailable'}</span><span className={selectedGame.output_files?.length ? 'is-positive' : 'is-muted'}><i />{selectedGame.output_files?.length || 0} output files</span><span className={selectedGame.data_processed ? 'is-positive' : 'is-warning'}><i />{selectedGame.data_processed ? 'Processed' : 'Not processed'}</span></div></div>
            <div className="offcanvas-section"><span className="offcanvas-label">Raw rows by table</span>{rawStats ? <div className="raw-table-counts">{Object.entries(rawStats.tables).map(([table, count]) => <div key={table}><span>{table}</span><strong>{count}</strong></div>)}<div className="raw-total"><span>Total rows</span><strong>{rawStats.total_rows}</strong></div></div> : <p className="offcanvas-help">Loading raw table counts...</p>}</div>
          </aside>
        </>
      )}
    </div>
  )
}
