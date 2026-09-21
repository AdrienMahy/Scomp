import { useState, useEffect } from 'react'
import { Card, Loading } from '../components'

export default function AnalyticsPage() {
  const [analyticsMode, setAnalyticsMode] = useState('players')
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(false)

  const mockPlayerStats = [
    { rank: 1, name: 'Antoine Griezmann', team: 'Red Star', goals: 12, assists: 5, games: 18, rating: 8.5 },
    { rank: 2, name: 'Kylian Mbappé', team: 'Red Star', goals: 11, assists: 3, games: 17, rating: 8.3 },
    { rank: 3, name: 'Karim Benzema', team: 'Reims', goals: 10, assists: 4, games: 18, rating: 8.1 },
    { rank: 4, name: 'Vincent Giroud', team: 'Clermont', goals: 9, assists: 2, games: 16, rating: 7.9 },
    { rank: 5, name: 'Olivier Giroud', team: 'Guingamp', goals: 8, assists: 3, games: 15, rating: 7.7 },
  ]

  const mockTeamStats = [
    { rank: 1, name: 'Red Star', wins: 14, draws: 2, losses: 2, gf: 45, ga: 18, gd: 27, points: 44, rating: 8.7 },
    { rank: 2, name: 'Reims', wins: 13, draws: 3, losses: 2, gf: 42, ga: 20, gd: 22, points: 42, rating: 8.4 },
    { rank: 3, name: 'Clermont', wins: 12, draws: 2, losses: 4, gf: 38, ga: 24, gd: 14, points: 38, rating: 8.1 },
    { rank: 4, name: 'Guingamp', wins: 11, draws: 3, losses: 4, gf: 35, ga: 26, gd: 9, points: 36, rating: 7.8 },
    { rank: 5, name: 'Dijon', wins: 10, draws: 2, losses: 6, gf: 32, ga: 28, gd: 4, points: 32, rating: 7.5 },
  ]

  useEffect(() => {
    // Simulate loading
    setLoading(true)
    setTimeout(() => {
      if (analyticsMode === 'players') {
        setStats(mockPlayerStats)
      } else {
        setStats(mockTeamStats)
      }
      setLoading(false)
    }, 500)
  }, [analyticsMode])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold mb-2">📊 Season Analytics</h2>
        <p className="text-neutral-600 dark:text-neutral-400">View player and team statistics for the season</p>
      </div>

      {/* Mode Toggle */}
      <Card title="📈 Analytics Mode">
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => setAnalyticsMode('players')}
            className={`px-4 py-3 rounded font-semibold transition-colors ${
              analyticsMode === 'players'
                ? 'bg-primary-500 text-white'
                : 'bg-light-200 dark:bg-dark-700 hover:bg-light-300'
            }`}
          >
            👥 Player Stats
          </button>
          <button
            onClick={() => setAnalyticsMode('teams')}
            className={`px-4 py-3 rounded font-semibold transition-colors ${
              analyticsMode === 'teams'
                ? 'bg-primary-500 text-white'
                : 'bg-light-200 dark:bg-dark-700 hover:bg-light-300'
            }`}
          >
            🏆 Team Stats
          </button>
        </div>
      </Card>

      {/* Loading State */}
      {loading && <Loading />}

      {/* Statistics Table */}
      {!loading && (
        <Card
          title={analyticsMode === 'players' ? '👥 Top Players' : '🏆 Team Standings'}
          subtitle={analyticsMode === 'players' ? '2026-2027 Season' : 'Ligue 2 Standings'}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-neutral-300 dark:border-dark-700">
                <tr>
                  <th className="text-left py-3 font-semibold">#</th>
                  <th className="text-left py-3 font-semibold">
                    {analyticsMode === 'players' ? 'Player' : 'Team'}
                  </th>
                  {analyticsMode === 'players' ? (
                    <>
                      <th className="text-center py-3 font-semibold">Team</th>
                      <th className="text-center py-3 font-semibold">Goals</th>
                      <th className="text-center py-3 font-semibold">Assists</th>
                      <th className="text-center py-3 font-semibold">GP</th>
                      <th className="text-right py-3 font-semibold">Rating</th>
                    </>
                  ) : (
                    <>
                      <th className="text-center py-3 font-semibold">W</th>
                      <th className="text-center py-3 font-semibold">D</th>
                      <th className="text-center py-3 font-semibold">L</th>
                      <th className="text-center py-3 font-semibold">GF</th>
                      <th className="text-center py-3 font-semibold">GA</th>
                      <th className="text-center py-3 font-semibold">GD</th>
                      <th className="text-right py-3 font-semibold">Pts</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {stats.map((stat) => (
                  <tr
                    key={stat.name}
                    className="border-b border-neutral-200 dark:border-dark-700 hover:bg-light-100 dark:hover:bg-dark-800"
                  >
                    <td className="py-3 font-semibold text-primary-500">{stat.rank}</td>
                    <td className="py-3 font-semibold">{stat.name}</td>

                    {analyticsMode === 'players' ? (
                      <>
                        <td className="text-center py-3 text-sm">{stat.team}</td>
                        <td className="text-center py-3 font-semibold text-accent-red">
                          {stat.goals}
                        </td>
                        <td className="text-center py-3">{stat.assists}</td>
                        <td className="text-center py-3">{stat.games}</td>
                        <td className="text-right py-3 font-semibold text-primary-500">
                          {stat.rating}
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="text-center py-3 text-primary-500 font-semibold">
                          {stat.wins}
                        </td>
                        <td className="text-center py-3">{stat.draws}</td>
                        <td className="text-center py-3 text-accent-red">{stat.losses}</td>
                        <td className="text-center py-3">{stat.gf}</td>
                        <td className="text-center py-3">{stat.ga}</td>
                        <td className="text-center py-3 font-semibold">{stat.gd}</td>
                        <td className="text-right py-3 font-semibold text-accent-gold">
                          {stat.points}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="mt-6 pt-4 border-t border-neutral-300 dark:border-dark-700">
            <p className="text-xs text-neutral-600 dark:text-neutral-400">
              {analyticsMode === 'players'
                ? 'GP = Games Played | Rating = Performance Rating (0-10)'
                : 'W = Wins | D = Draws | L = Losses | GF = Goals For | GA = Goals Against | GD = Goal Difference | Pts = Points'}
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}
