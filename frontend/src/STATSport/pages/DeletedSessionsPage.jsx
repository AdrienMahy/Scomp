import { useEffect, useState } from 'react'
import axios from 'axios'
import { XCircle } from 'lucide-react'
import { API_BASE } from '../api'

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })
}

export default function DeletedSessionsPage() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    axios.get(`${API_BASE}/physical/sessions/deleted?limit=500`)
      .then(response => setSessions(response.data || []))
      .catch(requestError => setError(requestError.response?.data?.detail || requestError.message))
      .finally(() => setLoading(false))
  }, [])

  return <div className="physical-page">
    <header className="physical-hero"><div><p className="eyebrow physical-eyebrow">PHYSICALDATA / DONNÉES</p><h1>Sessions supprimées</h1><p>Sessions qui ne sont plus renvoyées par l’API STATSports source.</p></div><div className="physical-live"><span /> {sessions.length} archivée(s)</div></header>
    <section className="physical-panel physical-deleted-sessions-panel">
      <div className="physical-panel-heading"><div><span className="physical-kicker">Réconciliation source</span><h2>Sessions absentes de l’API</h2></div><span className="physical-count">{sessions.length}</span></div>
      {loading && <div className="physical-empty">Chargement des sessions supprimées...</div>}
      {!loading && error && <div className="physical-empty">{error}</div>}
      {!loading && !error && !sessions.length && <div className="physical-empty">Aucune session supprimée détectée.</div>}
      {!loading && !error && sessions.length > 0 && <div className="physical-session-list">{sessions.map(session => <div className="physical-session-row physical-deleted-session-row" key={session.id}><div className="physical-session-mark"><XCircle size={15} aria-hidden="true" /></div><div className="physical-session-name"><strong>{session.activity_name || 'Activité sans nom'}</strong><small>Identifiant STATSports</small><code>{session.activity_id}</code></div><div className="physical-session-date"><small>Supprimée le</small><strong>{formatDate(session.deleted_at)}</strong></div><div className="physical-session-type">{session.team_name || '—'}</div></div>)}</div>}
    </section>
  </div>
}
