import { useState } from 'react'
import axios from 'axios'
import { ArrowRight, Database, Sparkles } from 'lucide-react'
import { Card, Badge, ErrorAlert, SuccessAlert } from '../../components'
import { API_BASE } from '../api'

export default function EnrichmentPage({ scope }) {
  const [loadingPlayers, setLoadingPlayers] = useState(false)
  const [errorPlayers, setErrorPlayers] = useState(null)
  const [successPlayers, setSuccessPlayers] = useState(null)
  const [resultPlayers, setResultPlayers] = useState(null)

  const handleEnrichPlayers = async () => {
    setLoadingPlayers(true)
    setErrorPlayers(null)
    setSuccessPlayers(null)
    setResultPlayers(null)

    try {
      const res = await axios.post(`${API_BASE}/players/scrape-players`, null, {
        params: { competition_id: scope?.competitionId, season_id: scope?.seasonId },
      })
      setResultPlayers(res.data)
      setSuccessPlayers('Joueurs enrichis avec succès depuis les matchs et l’API.')
    } catch (err) {
      setErrorPlayers(`Erreur : ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoadingPlayers(false)
    }
  }

  return (
    <div className="enrichment-page">
      <div className="enrichment-hero">
        <div>
          <p className="eyebrow">ESPACE DE TRAVAIL / ENRICHISSEMENT</p>
          <h1>Compléter les données</h1>
          <p>Rapprochez les profils joueurs et les informations d’équipe avec la source SportsDynamics.</p>
        </div>
      </div>

      <div className="enrichment-alerts">
        {errorPlayers && <ErrorAlert message={errorPlayers} />}
        {successPlayers && <SuccessAlert message={successPlayers} />}
      </div>

      <div className="enrichment-workspaces">
        <Card title="Enrichir les joueurs" subtitle="Compléter les profils liés aux matchs de la saison active">
          <button className="workspace-action" type="button" onClick={handleEnrichPlayers} disabled={loadingPlayers || !scope}>
            <span className="enrichment-action-icon"><Sparkles size={17} aria-hidden="true" /></span><div><strong>{loadingPlayers ? 'Enrichissement en cours...' : 'Lancer l’enrichissement'}</strong><small>{scope ? 'Interroger l’API et mettre à jour la base locale' : 'Sélectionnez d’abord une compétition et une saison'}</small></div><ArrowRight size={17} aria-hidden="true" />
          </button>
        </Card>

        <Card title="Périmètre du traitement" subtitle="Un rapprochement contrôlé avec les données locales">
          <div className="enrichment-scope-list">
            <div><span className="enrichment-scope-index">01</span><p><strong>Matchs actifs</strong><small>Les joueurs sont recherchés à partir des compositions enregistrées.</small></p></div>
            <div><span className="enrichment-scope-index">02</span><p><strong>Profils fournisseur</strong><small>Les informations SportsDynamics complètent les identifiants existants.</small></p></div>
            <div><span className="enrichment-scope-index">03</span><p><strong>Base préservée</strong><small>Les enregistrements sont mis à jour sans supprimer les données locales.</small></p></div>
          </div>
        </Card>
      </div>

      {resultPlayers && <Card title="Résultats de l’enrichissement" subtitle="Dernière exécution sur le périmètre sélectionné">
        <div className="enrichment-results">
          <div><span>Statut</span><Badge variant="success">{resultPlayers.status}</Badge></div>
          <div><span>Total en base</span><strong>{resultPlayers.total_players_in_db}</strong></div>
          <div><span>Créés</span><strong>{resultPlayers.created}</strong></div>
          <div><span>Mis à jour</span><strong>{resultPlayers.updated}</strong></div>
          <div><span>Ignorés</span><strong>{resultPlayers.skipped}</strong></div>
          <div className={resultPlayers.api_errors > 0 ? 'has-errors' : ''}><span>Erreurs API</span><strong>{resultPlayers.api_errors}</strong></div>
        </div>
        <p className="enrichment-result-message"><Database size={14} aria-hidden="true" /> {resultPlayers.message}</p>
      </Card>}
    </div>
  )
}
