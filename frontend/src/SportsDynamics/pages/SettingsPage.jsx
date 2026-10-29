import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { API_BASE } from '../api'

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
      .catch(() => setError('Impossible de charger le catalogue fournisseur. Vous pouvez toujours ajouter des identifiants manuellement.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(customScopes))
  }, [customScopes])

  const allScopes = useMemo(() => [...providerScopes, ...customScopes], [providerScopes, customScopes])
  const groupedScopes = useMemo(() => allScopes.reduce((groups, item) => {
    const key = `${item.competitionId}-${item.competitionName}`
    const existing = groups.find(group => group.key === key)
    if (existing) existing.seasons.push(item)
    else groups.push({ key, competitionId: item.competitionId, competitionName: item.competitionName, seasons: [item] })
    return groups
  }, []), [allScopes])

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
      setError('Les identifiants de compétition et de saison sont obligatoires.')
      return
    }
    const item = {
      key: `custom-${Date.now()}`,
      competitionId: form.competitionId.trim(),
      competitionName: form.competitionName.trim() || 'Compétition sans nom',
      seasonId: form.seasonId.trim(),
      seasonName: form.seasonName.trim() || 'Saison sans nom',
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
          <p className="eyebrow">CONFIGURATION DE L’ESPACE</p>
          <h1>Paramètres</h1>
          <p>Gérez les identifiants de compétition et de saison utilisés par le périmètre actif.</p>
        </div>
      </header>

      {error && <div className="settings-alert">{error}</div>}
      {saved && <div className="settings-toast">Périmètre actif mis à jour</div>}

      <div className="settings-layout">
        <div className="settings-catalog panel-surface">
          <div className="settings-panel-heading"><div><span className="section-label">CATALOGUE DES IDENTIFIANTS</span><h2>Périmètres disponibles</h2></div><span className="settings-count">{allScopes.length} périmètre(s)</span></div>
          {loading ? <p className="settings-empty">Chargement du catalogue fournisseur...</p> : allScopes.length === 0 ? <p className="settings-empty">Aucun périmètre configuré.</p> : <div className="scope-list">
            {groupedScopes.map(group => <section className="scope-group" key={group.key}>
              <header className="scope-group-heading"><div className="scope-icon">{group.competitionName.slice(0, 1).toUpperCase()}</div><div><strong>{group.competitionName}</strong><span>{group.seasons.length} saison{group.seasons.length > 1 ? 's' : ''}</span></div></header>
              <div className="scope-seasons">
                {group.seasons.map(item => {
                  const active = scope?.competitionId === item.competitionId && String(scope?.seasonId) === String(item.seasonId)
                  return <article className={`scope-row ${active ? 'is-active' : ''}`} key={item.key}>
                    <div className="scope-main"><strong>{item.seasonName}</strong><span>{item.source === 'Local' ? 'Ajout local' : 'Catalogue fournisseur'}</span></div>
                    <div className="scope-ids"><button type="button" onClick={() => copyId(item.competitionId)} title="Copier l’identifiant de compétition"><small>COMPÉTITION</small><code>{item.competitionId}</code></button><button type="button" onClick={() => copyId(item.seasonId)} title="Copier l’identifiant de saison"><small>SAISON</small><code>{item.seasonId}</code></button></div>
                    <button type="button" className="scope-select" aria-pressed={active} onClick={() => activateScope(item)}>{active ? 'Saison active' : 'Activer'}</button>
                    <span className="scope-remove-slot">{item.source === 'Local' && <button type="button" className="scope-remove" onClick={() => removeCustomScope(item.key)} title="Supprimer la compétition et la saison locales" aria-label={`Supprimer ${item.competitionName}, saison ${item.seasonName}`}>×</button>}</span>
                  </article>
                })}
              </div>
            </section>)}
          </div>}
        </div>

        <form className="settings-form panel-surface" onSubmit={addCustomScope}>
          <span className="section-label">CATALOGUE LOCAL</span>
          <h2>Ajout d’une compétition/saison</h2>
          <p className="settings-form-intro">Ajoutez une compétition et sa saison pour les rendre disponibles dans votre espace.</p>
          <div className="settings-form-group">
            <span>Compétition</span>
            <label>Nom<input name="competitionName" value={form.competitionName} onChange={updateForm} placeholder="Ligue 1" /></label>
            <label>Identifiant<input name="competitionId" value={form.competitionId} onChange={updateForm} placeholder="Identifiant de compétition" required /></label>
          </div>
          <div className="settings-form-group">
            <span>Saison</span>
            <label>Nom<input name="seasonName" value={form.seasonName} onChange={updateForm} placeholder="2026-2027" /></label>
            <label>Identifiant<input name="seasonId" value={form.seasonId} onChange={updateForm} placeholder="Identifiant de saison" required /></label>
          </div>
          <button className="settings-submit" type="submit"><span>+</span> Enregistrer et activer</button>
          <small className="settings-note">Cette compétition et cette saison seront enregistrées dans ce navigateur.</small>
        </form>
      </div>
    </section>
  )
}