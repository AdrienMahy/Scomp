import { useEffect, useState } from 'react'
import axios from 'axios'
import { RotateCcw } from 'lucide-react'
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
    <header className="physical-hero"><div><p className="eyebrow physical-eyebrow">PHYSICALDATA / DATA</p><h1>Deleted sessions</h1><p>Sessions no longer returned by the upstream STATSports API.</p></div><div className="physical-live"><span /> {sessions.length} archived</div></header>
    <section className="physical-panel physical-deleted-sessions-panel">
      <div className="physical-panel-heading"><div><span className="physical-kicker">Source reconciliation</span><h2>Sessions removed from API</h2></div><span className="physical-count">{sessions.length}</span></div>
      {loading && <div className="physical-empty">Loading deleted sessions...</div>}
      {!loading && error && <div className="physical-empty">{error}</div>}
      {!loading && !error && !sessions.length && <div className="physical-empty">No deleted sessions detected.</div>}
      {!loading && !error && sessions.length > 0 && <div className="physical-session-list">{sessions.map(session => <div className="physical-session-row physical-deleted-session-row" key={session.id}><div className="physical-session-mark"><RotateCcw size={14} /></div><div className="physical-session-name"><strong>{session.activity_name || 'Unnamed activity'}</strong><span>{session.activity_id}</span></div><div className="physical-session-date"><small>Deleted</small><strong>{formatDate(session.deleted_at)}</strong></div><div className="physical-session-type">{session.squad_name || session.squad_external_id || '—'}</div></div>)}</div>}
    </section>
  </div>
}
