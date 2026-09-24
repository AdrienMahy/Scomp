import { useState } from 'react'
import axios from 'axios'
import '../styles/GameMatchCard.css'
import { API_BASE } from '../api'

/**
 * GameMatchCard - Beautiful match display card
 * Shows: Round | Team A vs Team B | Score | Dates | Status
 */
export default function GameMatchCard({ game, onClick }) {
  const [scrapeLoading, setScrapeLoading] = useState(false)
  const [scrapeMessage, setScrapeMessage] = useState(null)
  // Use team data from API response, with fallback to parsing game.name
  const getTeams = () => {
    // If API provides team objects, use them
    if (game.home_team || game.away_team) {
      return {
        home: game.home_team || { name: 'Team A', brand: null },
        away: game.away_team || { name: 'Team B', brand: null }
      }
    }
    
    // Fallback: parse from game.name (format: "Team A vs Team B")
    if (!game.name) return { home: { name: 'Team A', brand: null }, away: { name: 'Team B', brand: null } }
    
    let parts = game.name.split(' vs ')
    if (parts.length !== 2) {
      parts = game.name.split('vs')
    }
    
    return {
      home: { name: (parts[0]?.trim() || 'Team A'), brand: null },
      away: { name: (parts[1]?.trim() || 'Team B'), brand: null }
    }
  }

  const teams = getTeams()
  const homeTeam = teams.home
  const awayTeam = teams.away

  // Extract data
  const round = game.round_name || 'N/A'
  const homeScore = game.home_score ?? '-'
  const awayScore = game.away_score ?? '-'
  const isProcessed = game.data_processed === true
  const startsAt = game.starts_at ? new Date(game.starts_at).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'N/A'
  // Use updated_at for process date (when data was last processed)
  const processedAt = game.updated_at ? new Date(game.updated_at).toLocaleDateString('fr-FR') : 'N/A'

  // Determine status badge
  const getStatusColor = () => {
    if (isProcessed) return 'status-treated'
    return 'status-scheduled'
  }

  const getStatusText = () => {
    if (isProcessed) return '✓ TREATED'
    return 'SCHEDULED'
  }

  // Force scrape handler
  const handleForceScrape = async (e) => {
    e.stopPropagation() // Don't trigger card onClick
    
    setScrapeLoading(true)
    setScrapeMessage(null)
    
    try {
      const response = await axios.post(`${API_BASE}/games/${game.id}/scrape-game`)
      setScrapeMessage({ type: 'success', text: `Queued · task ${response.data.task_id?.slice(0, 8) || 'created'}` })
      
      // Clear message after 3 seconds
      setTimeout(() => setScrapeMessage(null), 3000)
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || 'Force scrape failed'
      setScrapeMessage({ type: 'error', text: `❌ ${errorMsg}` })
      
      // Clear error after 5 seconds
      setTimeout(() => setScrapeMessage(null), 5000)
    } finally {
      setScrapeLoading(false)
    }
  }

  // Fallback logo (colored diamond)
  const TeamLogo = ({ team, side }) => {
    const colors = {
      HOME: '#e64040',
      AWAY: '#3B82F6', // Blue
    }
    const color = colors[side] || '#6B7280'

    const logoUrl = team?.logo_url || (team?.brand?.startsWith('http') ? team.brand : null)

    if (logoUrl) {
      return (
        <div className="team-logo-container">
          <img
            src={logoUrl}
            alt={team.name}
            className="team-logo-img"
            onError={(e) => {
              e.target.style.display = 'none'
              const sibling = e.target.nextElementSibling
              if (sibling) sibling.style.display = 'none'
            }}
          />
          <div
            className="team-logo-fallback"
            style={{ backgroundColor: color }}
          >
            {team.name?.charAt(0).toUpperCase()}
          </div>
        </div>
      )
    }

    return null
  }

  return (
    <div className="game-match-card" onClick={onClick}>
      {/* Round Badge */}
      <div className="round-badge">{round}</div>

      {/* Main Match Display */}
      <div className="match-container">
        {/* Home Team */}
        <div className="team-section home-team">
          <TeamLogo team={homeTeam} side="HOME" />
          <div className="team-info">
            <div className="team-name">{homeTeam?.name || 'Team A'}</div>
            <div className="team-brand">{homeTeam?.brand || ''}</div>
          </div>
        </div>

        {/* Score Section */}
        <div className="score-section">
          <div className="score">
            <span className="score-number">{homeScore}</span>
            <span className="score-separator">-</span>
            <span className="score-number">{awayScore}</span>
          </div>
          <div className={`status-badge ${getStatusColor()}`}>
            {getStatusText()}
          </div>
        </div>

        {/* Away Team */}
        <div className="team-section away-team">
          <div className="team-info">
            <div className="team-name">{awayTeam?.name || 'Team B'}</div>
            <div className="team-brand">{awayTeam?.brand || ''}</div>
          </div>
          <TeamLogo team={awayTeam} side="AWAY" />
        </div>
      </div>

      <div className="match-row-meta">
        <span>{startsAt}</span>
        <span className="match-files">{game.output_files?.length || 0} files</span>
      </div>
    </div>
  )
}
