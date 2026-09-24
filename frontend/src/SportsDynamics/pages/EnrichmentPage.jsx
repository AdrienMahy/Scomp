import { useState } from 'react'
import axios from 'axios'
import { Card, Button, Badge, Loading, ErrorAlert, SuccessAlert } from '../../components'
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
      setSuccessPlayers(`✅ Players enriched from games & API successfully!`)
    } catch (err) {
      setErrorPlayers(`Error: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoadingPlayers(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold mb-2">✨ Data Enrichment</h2>
        <p className="text-neutral-600 dark:text-neutral-400">Enrich Players and Teams data from SportsDynamics API</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Players Enrichment */}
        <Card title="👥 Players Enrichment" subtitle="Enrich players from games using SportsDynamics API">
          <div className="space-y-4">
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              This will:
            </p>
            <ul className="text-sm space-y-1 text-neutral-600 dark:text-neutral-400 list-disc list-inside">
              <li>Fetch all games from database (optionally filtered)</li>
              <li>Query SportsDynamics API for game squads</li>
              <li>Extract all player IDs from home and away squads</li>
              <li>Batch fetch player details from API</li>
              <li>Create/update players with positions, nationalities, photo, age, birthdate</li>
            </ul>

            <div className="pt-4">
              <Button
                onClick={handleEnrichPlayers}
                variant="primary"
                disabled={loadingPlayers}
              >
                {loadingPlayers ? '⏳ Enriching...' : '🚀 Enrich Players from API'}
              </Button>
            </div>

            {errorPlayers && <ErrorAlert message={errorPlayers} />}
            {successPlayers && <SuccessAlert message={successPlayers} />}

            {resultPlayers && (
              <div className="mt-4 p-4 bg-neutral-100 dark:bg-dark-800 rounded-lg">
                <h4 className="font-semibold mb-3 text-sm">📊 Enrichment Results:</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <Badge variant="success">{resultPlayers.status}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span>Total players in database:</span>
                    <span className="font-semibold">{resultPlayers.total_players_in_db}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Created:</span>
                    <span className="font-semibold">{resultPlayers.created}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Updated:</span>
                    <span className="font-semibold">{resultPlayers.updated}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Skipped:</span>
                    <span className="font-semibold">{resultPlayers.skipped}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Created:</span>
                    <span className="font-semibold text-accent-red">{resultPlayers.created}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Updated:</span>
                    <span className="font-semibold text-blue-600">{resultPlayers.updated}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>API errors:</span>
                    <span className={`font-semibold ${resultPlayers.api_errors > 0 ? 'text-red-600' : 'text-accent-red'}`}>
                      {resultPlayers.api_errors}
                    </span>
                  </div>
                  <div className="mt-3 pt-3 border-t border-neutral-300 dark:border-dark-700">
                    <p className="text-xs italic">{resultPlayers.message}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </Card>

      </div>

      {/* Info Section */}
      <Card title="ℹ️ About Enrichment" subtitle="How data enrichment works">
        <div className="space-y-3 text-sm text-neutral-600 dark:text-neutral-400">
          <p>
            <strong>Enrichment Process:</strong> The enrichment endpoints fetch data from the SportsDynamics API and merge it with existing records in the local database.
          </p>
          <p>
            <strong>Players:</strong> Collects all unique players from games in the database, queries the API, and updates records with complete player information.
          </p>
          <p>
            <strong>Teams:</strong> Collects all unique teams from games in the database, queries the API, and updates records with complete team information including logo URLs from S3.
          </p>
          <p>
            <strong>Safe Operation:</strong> Existing records are preserved and updated with new API data. New records are created only for teams/players found in games but not yet in the database.
          </p>
        </div>
      </Card>
    </div>
  )
}
