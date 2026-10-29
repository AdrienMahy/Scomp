import { useState, useEffect } from 'react'
import axios from 'axios'
import { ArrowRight, Play, Sparkles } from 'lucide-react'
import { Card, Badge, ErrorAlert, SuccessAlert } from '../../components'
import { API_BASE } from '../api'

const PARSER_OPTIONS = [
  { id: 'lineups', label: 'Compositions', description: 'Les équipes et les joueurs doivent déjà exister.' },
  { id: 'periods_phase', label: 'Périodes et évolution du score', description: 'Actualise les périodes, la chronologie du score et le contexte RGD.' },
  { id: 'distances', label: 'Distances des équipes et joueurs', description: 'Actualise les distances et les intervalles d’intensité.' },
  { id: 'events', label: 'Événements', description: 'Actualise les événements RGD, buts et remplacements.' },
  { id: 'fitness', label: 'Données physiques', description: 'Actualise les courses et leurs synthèses.' },
]

const STANDARD_PARSER_IDS = PARSER_OPTIONS.map(parser => parser.id)

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
      setError('Impossible de charger les journées.')
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
      return current.includes(parserId)
        ? current.filter(id => id !== parserId)
        : [...current, parserId]
    })
  }

  const handleScrape = async (type) => {
    if (!scope) {
      setError('Sélectionnez d’abord une compétition et une saison dans la saison active.')
      return
    }
    if (type === 'rounds' && selectedParsers.length === 0) {
      setError('Sélectionnez au moins un groupe de données.')
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
          `${roundsToScrape.length} journée(s) mise(s) en file avec ${selectedParsers.length} groupe(s) de données.`
        )
      } else if (type === 'players') {
        const response = await axios.post(`${API_BASE}/players/scrape-players`, null, {
          params: { competition_id: scope.competitionId, season_id: scope.seasonId },
        })
        setQueuedTasks([response.data])
        setSuccess('Enrichissement des joueurs mis en file.')
      }
      setSelectedRounds([])
    } catch (err) {
      setError(`Erreur : ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="scraping-page">
      <div className="scraping-hero">
        <div><p className="eyebrow">ESPACE DE TRAVAIL / COLLECTE</p><h1>Contrôle du pipeline</h1><p>Lancez un workflow sur la compétition et la saison actives.</p></div>
        <div className="scraping-context"><span className="status-dot" /><strong>{scope?.competitionName || 'Aucune compétition'}</strong><span>{scope?.seasonName || 'Sélectionnez une saison dans la navigation'}</span></div>
      </div>

      {/* Alerts */}
      <div className="space-y-3">
        {error && <ErrorAlert message={error} />}
        {success && <SuccessAlert message={success} />}
      </div>

      {/* Control Panel */}
      <div className="scraping-workspaces">
        <Card
          title="Collecter des journées"
          subtitle={`${selectedRounds.length} journée(s), ${selectedParsers.length} groupe(s) sélectionné(s)`}
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
                <h2 id="parser-selection-title">Groupes de données à traiter</h2>
                <p>Seuls les groupes sélectionnés et leurs fichiers nécessaires seront traités.</p>
              </div>
              <div className="parser-selection-actions">
                <button
                  type="button"
                  onClick={() => setSelectedParsers(STANDARD_PARSER_IDS)}
                  disabled={loading}
                >
                  Sélectionner les groupes standards
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedParsers([])}
                  disabled={loading}
                >
                  Effacer
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
            <span><Play size={17} aria-hidden="true" /></span><div><strong>Traiter les journées sélectionnées</strong><small>{scope ? 'Télécharger les fichiers requis et traiter les groupes choisis' : 'Sélectionnez d’abord une compétition et une saison'}</small></div><ArrowRight size={17} aria-hidden="true" />
          </button>
        </Card>

        <Card title="Enrichissement des joueurs" subtitle="Compléter les profils de la saison active">
          <div className="enrichment-workspace"><span className="workspace-symbol"><Sparkles size={18} aria-hidden="true" /></span><p>Enrichissez uniquement les joueurs liés aux matchs de la compétition et de la saison actives.</p></div>
          <button className="workspace-action" onClick={() => handleScrape('players')} disabled={loading || !scope}>
            <span><Sparkles size={17} aria-hidden="true" /></span><div><strong>Enrichir les joueurs</strong><small>{scope ? 'Mettre en file la tâche d’enrichissement' : 'Sélectionnez d’abord une compétition et une saison'}</small></div><ArrowRight size={17} aria-hidden="true" />
          </button>
        </Card>
      </div>

      {queuedTasks.length > 0 && <Card title="Exécutions en file" subtitle="Suivez la progression dans les journaux d’activité">
        <div className="queued-task-list">{queuedTasks.map(task => <div className="queued-task" key={task.task_id}><span className="status-dot" /><div><strong>{task.workflow}</strong>{Array.isArray(task.parsers) && <small>Groupes : {task.parsers.join(', ')}</small>}<small>{task.task_id}</small></div><Badge variant="warning">En file</Badge></div>)}</div>
      </Card>}

    </div>
  )
}
