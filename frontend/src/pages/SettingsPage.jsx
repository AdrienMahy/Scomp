import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

const API_BASE = '/api'
const STORAGE_KEY = 'scomp-custom-scopes'

function readCustomScopes() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return Array.isArray(stored) ? stored : []
  } catch {
    return []
  }
}

function normalizeProviderScopes(leagues) {
  return leagues.flatMap(league => (league.Seasons || []).map(season => ({
    key: `provider-${league.competitionId}-${season.seasonId}`,
    competitionId: String(league.competitionId),
    competitionName: league.Name,
    seasonId: String(season.seasonId),
    seasonName: season.name,
    source: 'SportsDynamics',
  })))
}

export default function SettingsPage({ scope, onScopeChange }) {
  const [providerScopes, setProviderScopes] = useState([])
  const [customScopes, setCustomScopes] = useState(readCustomScopes)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState({ competitionName: '', competitionId: '', seasonName: '', seasonId: '' })

  useEffect(() => {
    axios.get(`${API_BASE}/games/ids-config`)
      .then(response => setProviderScopes(normalizeProviderScopes(response.data.leagues || [])))
      .catch(() => setError('Unable to load the provider ID catalog. You can still add IDs manually.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(customScopes))
  }, [customScopes])

  const allScopes = useMemo(() => [...providerScopes, ...customScopes], [providerScopes, customScopes])

  const activateScope = (item) => {
    onScopeChange({
      competitionId: item.competitionId,
      competitionName: item.competitionName,
      seasonId: item.seasonId,
      seasonName: item.seasonName,
    })
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }

  const updateForm = event => setForm(previous => ({ ...previous, [event.target.name]: event.target.value }))

  const addCustomScope = event => {
    event.preventDefault()
    if (!form.competitionId.trim() || !form.seasonId.trim()) {
      setError('Competition ID and season ID are required.')
      return
    }
    const item = {
      key: `custom-${Date.now()}`,
      competitionId: form.competitionId.trim(),
      competitionName: form.competitionName.trim() || 'Unnamed competition',
      seasonId: form.seasonId.trim(),
      seasonName: form.seasonName.trim() || 'Unnamed season',
      source: 'Local',
    }
    setCustomScopes(previous => [...previous, item])
    setForm({ competitionName: '', competitionId: '', seasonName: '', seasonId: '' })
    setError('')
    activateScope(item)
  }

  const removeCustomScope = key => setCustomScopes(previous => previous.filter(item => item.key !== key))

  const copyId = value => navigator.clipboard?.writeText(value)

  return (
    <section className="settings-page">
      <header className="settings-header">
        <div>
          <p className="eyebrow">WORKSPACE CONFIGURATION</p>
          <h1>Settings</h1>
          <p>Manage competition and season IDs used by the active data scope.</p>
        </div>
        <div className="settings-active-badge"><span className="status-dot" /><div><small>ACTIVE SCOPE</small><strong>{scope?.competitionName || 'Not selected'} / {scope?.seasonName || 'No season'}</strong></div></div>
      </header>

      {error && <div className="settings-alert">{error}</div>}
      {saved && <div className="settings-toast">Active scope updated</div>}

      <div className="settings-layout">
        <div className="settings-catalog panel-surface">
          <div className="settings-panel-heading"><div><span className="section-label">ID CATALOG</span><h2>Available scopes</h2></div><span className="settings-count">{allScopes.length} scopes</span></div>
          {loading ? <p className="settings-empty">Loading provider catalog...</p> : allScopes.length === 0 ? <p className="settings-empty">No scopes configured yet.</p> : <div className="scope-list">
            {allScopes.map(item => {
              const active = scope?.competitionId === item.competitionId && String(scope?.seasonId) === String(item.seasonId)
              return <article className={`scope-row ${active ? 'is-active' : ''}`} key={item.key}>
                <div className="scope-icon">{item.competitionName.slice(0, 1).toUpperCase()}</div>
                <div className="scope-main"><strong>{item.competitionName}</strong><span>{item.seasonName} <em>{item.source}</em></span></div>
                <div className="scope-ids"><button type="button" onClick={() => copyId(item.competitionId)} title="Copy competition ID"><small>COMPETITION</small><code>{item.competitionId}</code></button><button type="button" onClick={() => copyId(item.seasonId)} title="Copy season ID"><small>SEASON</small><code>{item.seasonId}</code></button></div>
                <button type="button" className="scope-select" onClick={() => activateScope(item)}>{active ? 'Active' : 'Use scope'}</button>
                {item.source === 'Local' && <button type="button" className="scope-remove" onClick={() => removeCustomScope(item.key)} title="Remove local scope">×</button>}
              </article>
            })}
          </div>}
        </div>

        <form className="settings-form panel-surface" onSubmit={addCustomScope}>
          <span className="section-label">LOCAL CATALOG</span>
          <h2>Add IDs manually</h2>
          <p className="settings-form-intro">Keep a competition and season pair available even when it is not present in the provider catalog.</p>
          <label>Competition name<input name="competitionName" value={form.competitionName} onChange={updateForm} placeholder="Ligue 1" /></label>
          <label>Competition ID<input name="competitionId" value={form.competitionId} onChange={updateForm} placeholder="competition UUID" required /></label>
          <label>Season name<input name="seasonName" value={form.seasonName} onChange={updateForm} placeholder="2026 - 2027" /></label>
          <label>Season ID<input name="seasonId" value={form.seasonId} onChange={updateForm} placeholder="season UUID" required /></label>
          <button className="settings-submit" type="submit"><span>+</span> Save and activate scope</button>
          <small className="settings-note">Local entries are stored in this browser only.</small>
        </form>
      </div>
    </section>
  )
}