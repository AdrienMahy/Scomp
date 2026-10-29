import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Pause, Play, RefreshCw, StopCircle } from 'lucide-react'
import { Badge, Loading, ErrorAlert } from '../../components'
import { API_BASE } from '../api'

const statusLabels = { completed: 'Terminée', running: 'En cours', partial: 'Partielle', failed: 'Échouée', pending: 'En attente', skipped: 'Ignorée', cancelled: 'Annulée' }

function StatusBadge({ status }) {
  const variant = status === 'completed' ? 'success' : status === 'failed' ? 'error' : status === 'partial' ? 'warning' : 'warning'
  return <Badge variant={variant}>{statusLabels[status] || status}</Badge>
}

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function TaskCenterPage() {
  const [tasks, setTasks] = useState([])
  const [selected, setSelected] = useState(null)
  const [logs, setLogs] = useState([])
  const [gameStats, setGameStats] = useState([])
  const [filter, setFilter] = useState('all')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cancellingTaskId, setCancellingTaskId] = useState(null)

  async function loadTasks() {
    try {
      const response = await axios.get(`${API_BASE}/games/tasks/list?limit=25`)
      setTasks(response.data.tasks || [])
      if (selected) {
        const fresh = (response.data.tasks || []).find(task => task.id === selected.id)
        if (fresh) setSelected(fresh)
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message)
    } finally {
      setLoading(false)
    }
  }

  async function loadLogs(task) {
    if (!task) return
    try {
      const response = await axios.get(`${API_BASE}/games/tasks/${task.id}/logs`)
      setLogs(response.data.logs || [])
    } catch {
      setLogs([])
    }
  }

  async function loadGameStats(task) {
    if (!task) return
    try {
      const response = await axios.get(`${API_BASE}/games/tasks/${task.id}/game-stats`)
      setGameStats(response.data.games || [])
    } catch {
      setGameStats([])
    }
  }

  async function cancelTask(task) {
    if (!window.confirm(`Arrêter la tâche ${task.id.slice(0, 8)} ?`)) return
    setCancellingTaskId(task.id)
    try {
      await axios.post(`${API_BASE}/games/tasks/${task.id}/cancel`)
      await loadTasks()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message)
    } finally {
      setCancellingTaskId(null)
    }
  }

  useEffect(() => { loadTasks() }, [])
  useEffect(() => {
    loadLogs(selected)
    loadGameStats(selected)
  }, [selected?.id])
  useEffect(() => {
    if (!autoRefresh) return undefined
    const interval = setInterval(() => { loadTasks(); if (selected) { loadLogs(selected); loadGameStats(selected) } }, 4000)
    return () => clearInterval(interval)
  }, [autoRefresh, selected?.id])

  const visibleTasks = useMemo(() => filter === 'all' ? tasks : tasks.filter(task => task.status === filter), [tasks, filter])
  const latestErrors = logs.filter(log => log.level === 'ERROR')
  const phaseLogs = logs.filter(log => log.context && !log.item_id)

  return (
    <div className="task-center">
      <div className="task-center-header">
        <div><p className="eyebrow">SYSTÈME / SUIVI DES TÂCHES</p><h1>Historique d’exécution</h1><p>Retrouvez les collectes, leurs étapes et le résultat de chaque match.</p></div>
        <div className="task-center-actions"><button className="ghost-control" onClick={() => setAutoRefresh(!autoRefresh)}>{autoRefresh ? <><Pause size={14} aria-hidden="true" /> Actualisation active</> : <><Play size={14} aria-hidden="true" /> Actualisation en pause</>}</button><button className="ghost-control" onClick={loadTasks}><RefreshCw size={14} aria-hidden="true" /> Actualiser</button></div>
      </div>
      {error && <ErrorAlert message={error} />}
      <div className="task-filter-bar">
        {['all', 'running', 'completed', 'partial', 'failed', 'pending', 'cancelled'].map(status => <button key={status} className={filter === status ? 'selected' : ''} onClick={() => setFilter(status)}>{status === 'all' ? 'Toutes les tâches' : statusLabels[status]}</button>)}
      </div>
      {loading ? <Loading /> : <div className="task-center-grid">
        <section className="task-list-panel">
          <div className="task-panel-heading"><span>{visibleTasks.length} exécution(s)</span><small>Conservation : 30 jours</small></div>
          {visibleTasks.length === 0 && <div className="task-empty">Aucune exécution ne correspond à ce filtre.</div>}
          {visibleTasks.map(task => <div key={task.id} className={`task-list-item ${selected?.id === task.id ? 'is-selected' : ''}`} onClick={() => setSelected(task)} role="button" tabIndex={0} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') setSelected(task) }}>
            <div className="task-list-top"><strong>{task.workflow || 'Workflow de collecte'}</strong><div className="task-list-actions"><StatusBadge status={task.cancel_requested ? 'running' : task.status} />{['pending', 'running'].includes(task.status) && <button className="task-stop-button" onClick={event => { event.stopPropagation(); cancelTask(task) }} disabled={cancellingTaskId === task.id}><StopCircle size={13} aria-hidden="true" />{cancellingTaskId === task.id ? 'Arrêt...' : 'Arrêter'}</button>}</div></div>
            <span>{task.competition_id} · saison {task.season_id}</span>
            <div className="task-list-bottom"><span>{task.processed_items || 0}/{task.total_items || 0} élément(s)</span><span>{formatDate(task.created_at)}</span></div>
            <div className="task-progress"><i style={{ width: `${task.progress_percent || 0}%` }} /></div>
          </div>)}
        </section>
        <section className="task-detail-panel">
          {!selected ? <div className="task-empty task-detail-empty"><strong>Sélectionnez une exécution</strong><small>Ses étapes et les actions par match apparaîtront ici.</small></div> : <>
            <div className="task-detail-heading"><div><p className="eyebrow">TÂCHE <code className="task-id-code">{selected.id}</code></p><h2>{selected.workflow || 'Workflow de collecte'}</h2></div><StatusBadge status={selected.status} /></div>
            <div className="task-facts"><div><span>Journée</span><strong>{selected.round_name || '—'}</strong></div><div><span>ID de tâche</span><strong className="task-id-value" title={selected.id}>{selected.id}</strong></div><div><span>Étape actuelle</span><strong>{selected.current_phase || '—'}</strong></div><div><span>Match actuel</span><strong>{selected.current_item_id ? selected.current_item_id.slice(0, 12) : '—'}</strong></div><div><span>Démarrée</span><strong>{formatDate(selected.started_at)}</strong></div><div><span>Terminée</span><strong>{formatDate(selected.completed_at)}</strong></div></div>
            <div className="task-detail-progress"><div><span>Progression</span><strong>{selected.progress_percent?.toFixed(0) || 0}%</strong></div><div className="task-progress"><i style={{ width: `${selected.progress_percent || 0}%` }} /></div></div>
            {selected.error_message && <div className="task-error-box"><strong>Erreur de tâche</strong><span>{selected.error_message}</span></div>}
            {selected.workflow === 'autonomous_scrape' && selected.extra_metadata?.change_detection && <div className="task-detail-section"><div className="section-label"><span>Raisons des changements</span><small>{selected.extra_metadata.change_detection.affected_games_count || 0} matchs</small></div><div className="task-change-summary">{Object.entries(selected.extra_metadata.change_detection.reason_counts || {}).map(([reason, count]) => <span key={reason}><strong>{count}</strong> {reason.replaceAll('_', ' ')}</span>)}</div><div className="change-match-list">{(selected.extra_metadata.change_detection.affected_matches || []).map(match => <div className="change-match-row" key={match.id}><strong>{match.name || match.id}</strong><span>Journée {match.round || '—'} · {(match.change_reasons || []).map(reason => reason.replaceAll('_', ' ')).join(', ')}</span></div>)}</div></div>}
            <div className="task-detail-section"><div className="section-label"><span>Étapes</span><small>{phaseLogs.length} événement(s)</small></div><div className="phase-timeline">{phaseLogs.map(log => <div className="phase-event" key={log.id}><span className={`phase-dot phase-${log.level.toLowerCase()}`} /><div><strong>{log.context}</strong><p>{log.message}</p><small>{formatDate(log.timestamp)}</small></div></div>)}</div></div>
            <div className="task-detail-section"><div className="section-label"><span>Actions et erreurs par match</span><small>{latestErrors.length} erreur(s)</small></div><div className="action-log-list">{logs.filter(log => log.item_id || log.level === 'ERROR').map(log => <div className={`action-log ${log.level === 'ERROR' ? 'is-error' : ''}`} key={log.id}><div><strong>{log.item_name || log.item_id || log.context}</strong><span>{log.message}</span></div><small>{formatDate(log.timestamp)}</small></div>)}</div></div>
            <div className="task-detail-section"><div className="section-label"><span>Matchs collectés</span><small>{gameStats.length} match(s)</small></div><div className="scraped-games-list">{gameStats.length === 0 ? <p className="empty-state">Aucune statistique par match enregistrée.</p> : gameStats.map(game => <div className="scraped-game-row" key={game.game_id}><div><strong>{game.game_name}</strong><small>Journée {game.round} · {game.game_id}</small></div><div className="scraped-game-stats">{Object.entries(game.stats || {}).map(([table, counts]) => <span key={table}>{table}: <b>+{counts.inserted || 0} inséré(s)</b> <em>−{counts.deleted || 0} supprimé(s)</em></span>)}</div></div>)}</div></div>
          </>}
        </section>
      </div>}
    </div>
  )
}
