import { useState, useEffect } from 'react'
import axios from 'axios'
import { CalendarDays, Download, RefreshCw, Users, X } from 'lucide-react'
import { Card, Loading, ErrorAlert, Select } from '../../components'
import GameMatchCard from '../components/GameMatchCard'
import { API_BASE } from '../api'

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
        setError('Impossible de charger les matchs.')
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
      setScrapeMessage({ type: 'success', text: `Tâche mise en file · ${response.data.task_id?.slice(0, 8) || 'créée'}` })
    } catch (err) {
      setScrapeMessage({ type: 'error', text: err.response?.data?.detail || err.message })
    } finally {
      setScrapeLoading(false)
    }
  }

  const processedGames = games.filter(game => game.data_processed === true).length
  const gamesWithFiles = games.filter(game => game.output_files?.length > 0).length
  const pendingGames = Math.max(games.length - processedGames, 0)

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
        <div>
          <p className="eyebrow">ESPACE DE TRAVAIL / MATCHS</p>
          <h2 className="matches-title">Registre des matchs</h2>
          <p className="matches-intro">Consultez les rencontres traitées et relancez un traitement ciblé.</p>
        </div>
        <button className="matches-refresh-button" type="button" onClick={fetchGames} disabled={loading}>
          <RefreshCw size={15} aria-hidden="true" className={loading ? 'is-spinning' : ''} />
          Actualiser
        </button>
      </div>

      <div className="matches-overview" aria-label="Synthèse de la journée sélectionnée">
        <div className="matches-overview-item matches-overview-total"><span>Total affiché</span><strong>{games.length}</strong><small>match{games.length > 1 ? 's' : ''}</small></div>
        <div className="matches-overview-item matches-overview-processed"><span>Traités</span><strong>{processedGames}</strong><small>dans la base locale</small></div>
        <div className="matches-overview-item matches-overview-files"><span>Fichiers disponibles</span><strong>{gamesWithFiles}</strong><small>réponses fournisseur</small></div>
        <div className="matches-overview-item matches-overview-pending"><span>À vérifier</span><strong>{pendingGames}</strong><small>match{pendingGames > 1 ? 's' : ''} restant{pendingGames > 1 ? 's' : ''}</small></div>
      </div>

      {/* Filters */}
      <Card title="Filtres du registre" subtitle="Affinez la vue de la compétition">
        <div className="matches-filter-grid">
          {/* Filter Mode */}
          <div className="flex gap-2">
            <button
              onClick={() => { setFilterMode('round'); setSelectedFilter(rounds[0] || '1') }}
              aria-pressed={filterMode === 'round'}
                className={`filter-toggle ${
                filterMode === 'round'
                  ? 'bg-primary-500 text-white'
                  : 'bg-light-200 dark:bg-dark-700 hover:bg-light-300'
              }`}
            >
              <CalendarDays size={15} aria-hidden="true" />
              Par journée
            </button>
            <button
              onClick={() => { setFilterMode('team'); setSelectedFilter(teams[0]?.value || '') }}
              aria-pressed={filterMode === 'team'}
                className={`filter-toggle ${
                filterMode === 'team'
                  ? 'bg-primary-500 text-white'
                  : 'bg-light-200 dark:bg-dark-700 hover:bg-light-300'
              }`}
            >
              <Users size={15} aria-hidden="true" />
              Par équipe
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
              label="Équipe"
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
            <span className="matches-list-label">{games.length} match{games.length > 1 ? 's' : ''} trouvé{games.length > 1 ? 's' : ''}</span>
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
          <Card title="Aucun match trouvé">
          <p className="text-neutral-600 dark:text-neutral-400">Aucun match ne correspond au filtre sélectionné.</p>
        </Card>
      )}

      {selectedGame && (
        <>
          <button className="offcanvas-backdrop" onClick={() => setSelectedGame(null)} aria-label="Fermer les détails du match" />
          <aside className="match-offcanvas" aria-label="Détails du match">
            <div className="offcanvas-header">
              <div><p className="eyebrow">MATCH / DÉTAILS</p><h3>Informations du match</h3></div>
              <button className="offcanvas-close" onClick={() => setSelectedGame(null)} aria-label="Fermer"><X size={20} aria-hidden="true" /></button>
            </div>
            <div className="offcanvas-match-name">{selectedGame.name}</div>
            <div className="offcanvas-score"><strong>{selectedGame.home_score ?? '—'}</strong><span>:</span><strong>{selectedGame.away_score ?? '—'}</strong></div>
            <div className="offcanvas-status-row"><span>Provider status</span><strong>{selectedGame.status?.rgd_status || selectedGame.status?.ugd_status || (selectedGame.data_processed ? 'PROCESSED' : 'PENDING')}</strong></div>
            <button className="offcanvas-scrape-button" onClick={scrapeSelectedGame} disabled={scrapeLoading}>
              <RefreshCw size={16} aria-hidden="true" />
              {scrapeLoading ? 'Mise en file...' : 'Relancer le traitement'}
            </button>
            {scrapeMessage && <div className={`offcanvas-task-message ${scrapeMessage.type}`}>{scrapeMessage.text}</div>}
            <a className="offcanvas-download-button" href={`${API_BASE}/games/${selectedGame.id}/download-json`} download>
              <Download size={16} aria-hidden="true" /> Télécharger les fichiers JSON
            </a>
            <div className="offcanvas-section"><span className="offcanvas-label">Identifiants</span><dl>
              <dt>Game ID</dt><dd>{selectedGame.id}</dd>
              <dt>ID équipe domicile</dt><dd>{selectedGame.home_team?.id || '—'}</dd>
              <dt>ID équipe extérieure</dt><dd>{selectedGame.away_team?.id || '—'}</dd>
            </dl></div>
            <div className="offcanvas-section"><span className="offcanvas-label">Chronologie</span><dl>
              <dt>Date du match</dt><dd>{selectedGame.starts_at ? new Date(selectedGame.starts_at).toLocaleString('fr-FR') : '—'}</dd>
              <dt>Dernier traitement</dt><dd>{selectedGame.updated_at ? new Date(selectedGame.updated_at).toLocaleString('fr-FR') : '—'}</dd>
              <dt>Création en base</dt><dd>{selectedGame.created_at ? new Date(selectedGame.created_at).toLocaleString('fr-FR') : '—'}</dd>
            </dl></div>
            <div className="offcanvas-section"><span className="offcanvas-label">Disponibilité des données</span><p className="offcanvas-help">La disponibilité locale indique si ce match a été traité et enregistré.</p><div className="offcanvas-chips"><span className={selectedGame.data_processed ? 'is-positive' : selectedGame.status?.available ? 'is-positive' : 'is-negative'}><i />{selectedGame.data_processed ? 'Données locales disponibles' : selectedGame.status?.available ? 'Données fournisseur disponibles' : 'Données fournisseur indisponibles'}</span><span className={selectedGame.output_files?.length ? 'is-positive' : 'is-muted'}><i />{selectedGame.output_files?.length || 0} fichier(s) de sortie</span><span className={selectedGame.data_processed ? 'is-positive' : 'is-warning'}><i />{selectedGame.data_processed ? 'Traité' : 'Non traité'}</span></div></div>
            <div className="offcanvas-section"><span className="offcanvas-label">Lignes par table</span>{rawStats ? <div className="raw-table-counts">{Object.entries(rawStats.tables).map(([table, count]) => <div key={table}><span>{table}</span><strong>{count}</strong></div>)}<div className="raw-total"><span>Total des lignes</span><strong>{rawStats.total_rows}</strong></div></div> : <p className="offcanvas-help">Chargement des compteurs...</p>}</div>
          </aside>
        </>
      )}
    </div>
  )
}
