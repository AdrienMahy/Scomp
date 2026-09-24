import { useState, useEffect } from 'react';
import axios from 'axios';
import './AutomationPage.css';
import AutomationConfigPage from './AutomationConfigPage';
import { API_BASE } from '../api';

/**
 * AutomationPage - Manage and monitor smart scraping automation
 * 
 * Features:
 * - View automation status and configuration
 * - Monitor scraping statistics and trends
 * - Trigger manual scraping cycles
 * - View recent scraping logs
 * - Visual indicators for automation health
 */
export default function AutomationPage({ onNavigate }) {
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [lastScrape, setLastScrape] = useState(null);
  const [automationConfigs, setAutomationConfigs] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [runningCycle, setRunningCycle] = useState(false);
  const [cycleResult, setCycleResult] = useState(null);
  const [showConfigPanel, setShowConfigPanel] = useState(false);

  const formatMetric = (value, suffix = '') => {
    if (typeof value !== 'number' || Number.isNaN(value)) return '—'
    return `${value.toFixed(1)}${suffix}`
  }

  const parseApiDate = (value) => {
    if (!value) return null
    const normalizedValue = typeof value === 'string' && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)
      ? `${value}Z`
      : value
    const date = new Date(normalizedValue)
    return Number.isNaN(date.getTime()) ? null : date
  }

  const formatDate = (value) => {
    const date = parseApiDate(value)
    return date ? date.toLocaleString() : '—'
  }

  // Fetch all automation data
  const fetchAutomationData = async () => {
    try {
      setError(null);
      
      const [statusResp, configResp, statsResp, logsResp, lastScrapeResp, configurationsResp] = await Promise.all([
        axios.get(`${API_BASE}/automation/status`),
        axios.get(`${API_BASE}/automation/config`),
        axios.get(`${API_BASE}/automation/statistics?hours=24`),
        axios.get(`${API_BASE}/automation/logs?limit=10&hours=24`),
        axios.get(`${API_BASE}/automation/last-scrape`),
        axios.get(`${API_BASE}/automation/configurations`),
      ]);
      
      setStatus(statusResp.data);
      setConfig(configResp.data);
      setStats(statsResp.data);
      setLogs(logsResp.data.logs || []);
      setLastScrape(lastScrapeResp.data);
      setAutomationConfigs(configurationsResp.data || []);
      setLoading(false);
    } catch (err) {
      console.error('Fetch error:', err);
      setError(`Failed to load automation data: ${err.response?.data?.detail || err.message}`);
      setLoading(false);
    }
  };

  // Trigger immediate scraping cycle
  const triggerScrapeCycle = async () => {
    try {
      setRunningCycle(true);
      setCycleResult(null);
      
      const activeCompetitions = config?.active_competitions || []
      const results = await Promise.all(activeCompetitions.map(competition => axios.post(`${API_BASE}/games/scrape-autonome`, {
        competition_id: competition.id,
        season_id: competition.season_id,
      })))
      
      setCycleResult({
        status: 'success',
        message: `${results.length} autonomous task(s) started`,
        data: results.map(response => response.data),
        timestamp: new Date(),
      });
      
      // Refresh data after a delay
      setTimeout(fetchAutomationData, 1000);
    } catch (err) {
      console.error('Scrape cycle error:', err);
      setCycleResult({
        status: 'error',
        message: err.response?.data?.message || err.message,
        error: err.response?.data?.error || err.message,
        timestamp: new Date(),
      });
    } finally {
      setRunningCycle(false);
    }
  };

  // Setup auto-refresh
  useEffect(() => {
    fetchAutomationData();
    
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchAutomationData, 5000); // Refresh every 5 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  if (loading) {
    return (
      <div className="automation-page flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="spinner mb-4"></div>
          <p>Loading automation data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="automation-page">
      {/* Header */}
      <div className="automation-header mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold">🤖 Smart Scraping Automation</h1>
            <p className="text-gray-400 mt-2">Manage your intelligent scraping pipeline</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-6">
          ⚠️ {error}
        </div>
      )}

      {showConfigPanel && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/60"
          onClick={() => setShowConfigPanel(false)}
        >
          <div
            className="h-full w-full max-w-2xl bg-dark-900 shadow-2xl"
            onClick={event => event.stopPropagation()}
          >
            <AutomationConfigPage
              panel
              onClose={() => setShowConfigPanel(false)}
            />
          </div>
        </div>
      )}

      {/* Status Cards Grid */}
      <div className="automation-cards grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* Status Card */}
        <div className="automation-card bg-dark-800 border border-dark-700 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Status</p>
              <h3 className="text-2xl font-bold mt-2">
                {status?.is_enabled ? '✅ Active' : '❌ Inactive'}
              </h3>
            </div>
            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
              status?.is_enabled ? 'bg-accent-red/20' : 'bg-red-900'
            }`}>
              {status?.is_enabled ? '🟢' : '🔴'}
            </div>
          </div>
        </div>

        {/* Scrape Interval Card */}
        <div className="automation-card bg-dark-800 border border-dark-700 rounded-lg p-6">
          <p className="text-gray-400 text-sm">Scrape Interval</p>
          <h3 className="text-3xl font-bold mt-2">{config?.scrape_interval_minutes} min</h3>
          <p className="text-gray-500 text-xs mt-2">Between each cycle</p>
        </div>

        {/* Active Competitions Card */}
        <div className="automation-card bg-dark-800 border border-dark-700 rounded-lg p-6">
          <p className="text-gray-400 text-sm">Active Competitions</p>
          <h3 className="text-3xl font-bold mt-2">{status?.active_competitions}</h3>
          <p className="text-gray-500 text-xs mt-2">
            {config?.active_competitions?.map(c => c.name).join(', ')}
          </p>
        </div>

        {/* Games in DB Card */}
        <div className="automation-card bg-dark-800 border border-dark-700 rounded-lg p-6">
          <p className="text-gray-400 text-sm">Games in DB</p>
          <h3 className="text-3xl font-bold mt-2">{status?.total_games_in_db}</h3>
          <p className="text-gray-500 text-xs mt-2">Tracked games</p>
        </div>
      </div>

      {/* Automation Configurations */}
      <div className="bg-dark-800 border border-dark-700 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">⚙️ Configurations</h2>
          <button
            onClick={() => setShowConfigPanel(true)}
            className="text-accent-red text-sm font-semibold hover:text-primary-600"
          >
            Manage
          </button>
        </div>

        {automationConfigs.length === 0 ? (
          <p className="text-gray-400">No configurations yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700">
                  <th className="text-left py-2 pr-4 text-gray-400 font-semibold">Configuration</th>
                  <th className="text-left py-2 pr-4 text-gray-400 font-semibold">Competition</th>
                  <th className="text-left py-2 pr-4 text-gray-400 font-semibold">Season</th>
                  <th className="text-left py-2 pr-4 text-gray-400 font-semibold">Last execution</th>
                  <th className="text-left py-2 text-gray-400 font-semibold">Next refresh</th>
                </tr>
              </thead>
              <tbody>
                {automationConfigs.map(configuration => (
                  <tr key={configuration.id} className="border-b border-dark-700 last:border-0">
                    <td className="py-3 pr-4 text-white font-semibold">
                      <span className={configuration.enabled ? 'text-accent-red' : 'text-gray-500'}>
                        {configuration.enabled ? '●' : '○'}
                      </span>{' '}
                      {configuration.name}
                    </td>
                    <td className="py-3 pr-4 text-gray-300">{configuration.competition_name}</td>
                    <td className="py-3 pr-4 text-gray-300">{configuration.season_name || '—'}</td>
                    <td className="py-3 pr-4 text-gray-400">
                      {configuration.last_execution_at
                        ? formatDate(configuration.last_execution_at)
                        : 'Not run yet'}
                    </td>
                    <td className="py-3 text-gray-400">
                      {configuration.enabled
                        ? configuration.next_refresh_at
                          ? formatDate(configuration.next_refresh_at)
                          : 'Waiting for Beat'
                        : 'Disabled'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Last Scrape Info */}
      {lastScrape && (
        <div className="bg-dark-800 border border-dark-700 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">📊 Last Scraping Execution</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-gray-400 text-sm">Executed At</p>
              <p className="text-white font-mono text-sm mt-1">
                {lastScrape.executed_at 
                  ? formatDate(lastScrape.executed_at)
                  : 'Never'
                }
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Status</p>
              <p className="text-white text-sm mt-1">
                {lastScrape.status === 'success' ? '✅ Success' : '❌ Error'}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Games Found</p>
              <p className="text-white text-sm mt-1">{lastScrape.games_count || 0}</p>
            </div>
          </div>
          {lastScrape.error_message && (
            <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mt-4">
              <strong>Error:</strong> {lastScrape.error_message}
            </div>
          )}
        </div>
      )}

      {/* Statistics */}
      {stats && (
        <div className="bg-dark-800 border border-dark-700 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">📈 Statistics (Last 24 Hours)</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-700 rounded p-4">
              <p className="text-gray-400 text-sm">Total Scrapes</p>
              <p className="text-3xl font-bold mt-2">{stats.total_scrapes || 0}</p>
            </div>
            <div className="bg-dark-700 rounded p-4">
              <p className="text-gray-400 text-sm">Successful</p>
              <p className="text-3xl font-bold text-accent-red mt-2">{stats.successful || 0}</p>
            </div>
            <div className="bg-dark-700 rounded p-4">
              <p className="text-gray-400 text-sm">Failed</p>
              <p className="text-3xl font-bold text-red-400 mt-2">{stats.failed || 0}</p>
            </div>
            <div className="bg-dark-700 rounded p-4">
              <p className="text-gray-400 text-sm">Success Rate</p>
              <p className="text-3xl font-bold text-blue-400 mt-2">
                {typeof stats.success_rate_percent === 'number' ? formatMetric(stats.success_rate_percent, '%') : '—'}
              </p>
            </div>
            <div className="bg-dark-700 rounded p-4 md:col-span-2">
              <p className="text-gray-400 text-sm">Games Processed</p>
              <p className="text-3xl font-bold text-purple-400 mt-2">
                {stats.total_games_processed || 0}
              </p>
            </div>
            <div className="bg-dark-700 rounded p-4 md:col-span-2">
              <p className="text-gray-400 text-sm">Avg Games/Scrape</p>
              <p className="text-3xl font-bold text-accent-red mt-2">
                {formatMetric(stats.avg_games_per_scrape)}
              </p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
