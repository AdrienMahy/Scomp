import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../api';

export default function AutomationConfigPage({ panel = false, onClose }) {
  const [configs, setConfigs] = useState([]);
  const [competitions, setCompetitions] = useState([]);
  const [seasons, setSeasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [runningConfigId, setRunningConfigId] = useState(null);
  const [runResult, setRunResult] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    competition_id: '',
    competition_name: '',
    season_id: '',
    season_name: '',
    provider: 'sportsdynamics',
    scrape_interval_minutes: 20,
    enabled: true,
    look_ahead_days: 7,
    look_back_days: 1,
    live_game_window_minutes: 120,
    task_timeout_seconds: 1800,
  });

  // Fetch configurations
  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/automation/configurations`);
      setConfigs(response.data);
      setError(null);
    } catch (err) {
      setError(`Failed to load configurations: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchCompetitions = async () => {
    try {
      const response = await axios.get(`${API_BASE}/competitions`);
      setCompetitions(response.data);
    } catch (err) {
      setError(`Failed to load competitions: ${err.message}`);
    }
  };

  const fetchSeasons = async (competitionId) => {
    if (!competitionId) {
      setSeasons([]);
      return;
    }

    try {
      const response = await axios.get(`${API_BASE}/competitions/${competitionId}/seasons`);
      setSeasons(response.data);
    } catch (err) {
      setSeasons([]);
      setError(`Failed to load seasons: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchConfigs();
    fetchCompetitions();
  }, []);

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value) : value,
    }));
  };

  const handleCompetitionChange = async (e) => {
    const competitionId = e.target.value;
    const competition = competitions.find(item => item.id === competitionId);
    setFormData(prev => ({
      ...prev,
      competition_id: competitionId,
      competition_name: competition?.name || '',
      season_id: '',
      season_name: '',
    }));
    await fetchSeasons(competitionId);
  };

  const handleSeasonChange = (e) => {
    const season = seasons.find(item => item.id === e.target.value);
    setFormData(prev => ({
      ...prev,
      season_id: e.target.value,
      season_name: season?.name || '',
    }));
  };

  // Create or update configuration
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingId) {
        await axios.put(`${API_BASE}/automation/configurations/${editingId}`, formData);
      } else {
        await axios.post(`${API_BASE}/automation/configurations`, formData);
      }
      
      // Reset form and refresh list
      setShowForm(false);
      setEditingId(null);
      setFormData({
        name: '',
        description: '',
        competition_id: '',
        competition_name: '',
        season_id: '',
        season_name: '',
        provider: 'sportsdynamics',
        scrape_interval_minutes: 20,
        enabled: true,
        look_ahead_days: 7,
        look_back_days: 1,
        live_game_window_minutes: 120,
        task_timeout_seconds: 1800,
      });
      await fetchConfigs();
    } catch (err) {
      setError(`Failed to save configuration: ${err.message}`);
    }
  };

  // Edit configuration
  const handleEdit = (config) => {
    const matchingCompetition = competitions.find(
      competition => competition.id === config.competition_id
        || competition.name.toLowerCase() === config.competition_name?.toLowerCase()
    );

    setEditingId(config.id);
    setFormData({
      ...config,
      competition_id: matchingCompetition?.id || '',
      competition_name: matchingCompetition?.name || '',
      season_id: matchingCompetition ? config.season_id : '',
      season_name: matchingCompetition ? (config.season_name || '') : '',
    });
    setError(matchingCompetition ? null : 'Cette configuration utilise une ancienne compétition. Sélectionnez une compétition disponible dans la base.');
    fetchSeasons(matchingCompetition?.id);
    setShowForm(true);
  };

  // Delete configuration
  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this configuration?')) return;
    
    try {
      await axios.delete(`${API_BASE}/automation/configurations/${id}`);
      await fetchConfigs();
    } catch (err) {
      setError(`Failed to delete configuration: ${err.message}`);
    }
  };

  const handleRunConfiguration = async (configuration) => {
    try {
      setRunningConfigId(configuration.id);
      setRunResult(null);
      const response = await axios.post(`${API_BASE}/games/scrape-autonome`, {
        competition_id: configuration.competition_id,
        season_id: configuration.season_id,
      });
      setRunResult({
        status: 'success',
        message: `${configuration.name} launched (task ${response.data.task_id?.slice(0, 8) || 'queued'})`,
      });
    } catch (err) {
      setRunResult({
        status: 'error',
        message: err.response?.data?.detail || err.message,
      });
    } finally {
      setRunningConfigId(null);
    }
  };

  // Cancel editing
  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setFormData({
      name: '',
      description: '',
      competition_id: '',
      competition_name: '',
      season_id: '',
      season_name: '',
      provider: 'sportsdynamics',
      scrape_interval_minutes: 20,
      enabled: true,
      look_ahead_days: 7,
      look_back_days: 1,
      live_game_window_minutes: 120,
      task_timeout_seconds: 1800,
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="spinner mb-4"></div>
          <p>Loading configurations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={panel ? 'automation-config-page h-full overflow-y-auto p-6' : 'automation-config-page p-6'}>
      {/* Header */}
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">⚙️ Automation Configurations</h1>
          <p className="text-gray-400">Manage your scraping schedules and parameters</p>
        </div>
        {panel && (
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl leading-none"
            aria-label="Close configuration panel"
          >
            ×
          </button>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-6">
          ⚠️ {error}
        </div>
      )}

      {runResult && (
        <div className={`px-4 py-3 rounded mb-6 ${runResult.status === 'success'
          ? 'bg-accent-red/20 border border-accent-red text-white'
          : 'bg-red-900 border border-red-700 text-red-100'}`}>
          {runResult.status === 'success' ? '✅' : '⚠️'} {runResult.message}
        </div>
      )}

      {/* Create/Edit Form */}
      {showForm && (
        <div className="bg-dark-800 border border-dark-700 rounded-lg p-6 mb-6">
          <h2 className="text-2xl font-bold mb-4">
            {editingId ? '✏️ Edit Configuration' : '➕ New Configuration'}
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Basic Info Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Configuration Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                  placeholder="e.g., Ligue 2 2026-2027"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Description
                </label>
                <input
                  type="text"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                  placeholder="Optional description"
                />
              </div>
            </div>

            {/* Competition Info Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Competition *
                </label>
                <select
                  name="competition_id"
                  value={formData.competition_id}
                  onChange={handleCompetitionChange}
                  required
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                >
                  <option value="" disabled>Select a competition</option>
                  {competitions.map(competition => (
                    <option key={competition.id} value={competition.id}>
                      {competition.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Season *
                </label>
                <select
                  name="season_id"
                  value={formData.season_id}
                  onChange={handleSeasonChange}
                  required
                  disabled={!formData.competition_id || seasons.length === 0}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                >
                  <option value="" disabled>
                    {!formData.competition_id
                      ? 'Select a competition first'
                      : seasons.length === 0
                        ? 'No seasons available'
                        : 'Select a season'}
                  </option>
                  {seasons.map(season => (
                    <option key={season.id} value={season.id}>
                      {season.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <p className="text-gray-500 text-xs mb-2">
                  {seasons.length} season{seasons.length === 1 ? '' : 's'} available
                </p>
              </div>
            </div>

            {/* Schedule Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Scrape Interval (minutes) *
                </label>
                <input
                  type="number"
                  name="scrape_interval_minutes"
                  value={formData.scrape_interval_minutes}
                  onChange={handleInputChange}
                  required
                  min="1"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Provider *
                </label>
                <select
                  name="provider"
                  value={formData.provider}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                >
                  <option value="sportsdynamics">SportsDynamics</option>
                  <option value="perform">Perform</option>
                  <option value="secondspectrum">SecondSpectrum</option>
                </select>
              </div>
            </div>

            {/* Time Windows Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Look-Ahead Days *
                </label>
                <input
                  type="number"
                  name="look_ahead_days"
                  value={formData.look_ahead_days}
                  onChange={handleInputChange}
                  required
                  min="1"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Look-Back Days *
                </label>
                <input
                  type="number"
                  name="look_back_days"
                  value={formData.look_back_days}
                  onChange={handleInputChange}
                  required
                  min="0"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Live Game Window (min) *
                </label>
                <input
                  type="number"
                  name="live_game_window_minutes"
                  value={formData.live_game_window_minutes}
                  onChange={handleInputChange}
                  required
                  min="1"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                />
              </div>
            </div>

            {/* Task Timeout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Task Timeout (seconds) *
                </label>
                <input
                  type="number"
                  name="task_timeout_seconds"
                  value={formData.task_timeout_seconds}
                  onChange={handleInputChange}
                  required
                  min="60"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:border-accent-red"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    name="enabled"
                    checked={formData.enabled}
                    onChange={handleInputChange}
                    className="w-4 h-4 accent-accent-red"
                  />
                  <span className="text-sm font-semibold text-gray-300">Enable this configuration</span>
                </label>
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 mt-6">
              <button
                type="submit"
                className="px-6 py-2 bg-accent-red text-white rounded font-semibold hover:bg-primary-600 transition-colors"
              >
                {editingId ? '💾 Update' : '✅ Create'}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="px-6 py-2 bg-gray-700 text-gray-300 rounded font-semibold hover:bg-gray-600 transition-colors"
              >
                ❌ Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Create Button (when form is hidden) */}
      {!showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="mb-6 px-4 py-2 bg-accent-red text-white rounded font-semibold hover:bg-primary-600 transition-colors"
        >
          ➕ New Configuration
        </button>
      )}

      {/* Configurations List */}
      <div className="space-y-4">
        {configs.length === 0 ? (
          <div className="bg-dark-800 border border-dark-700 rounded-lg p-8 text-center">
            <p className="text-gray-400 text-lg">No configurations yet.</p>
            <p className="text-gray-500 text-sm mt-2">Create your first automation configuration to get started.</p>
          </div>
        ) : (
          configs.map(config => (
            <div
              key={config.id}
              className="bg-dark-800 border border-dark-700 rounded-lg p-6 hover:border-accent-red/50 transition-colors"
            >
              {/* Config Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-xl font-bold text-white">{config.name}</h3>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      config.enabled
                        ? 'bg-accent-red/20 text-accent-red'
                        : 'bg-gray-700 text-gray-400'
                    }`}>
                      {config.enabled ? '✅ Enabled' : '❌ Disabled'}
                    </span>
                  </div>
                  {config.description && (
                    <p className="text-gray-400 text-sm">{config.description}</p>
                  )}
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleRunConfiguration(config)}
                    disabled={runningConfigId === config.id || !config.enabled}
                    className="px-3 py-1 bg-primary-500 text-white rounded text-sm hover:bg-primary-600 transition-colors disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed"
                    title={config.enabled ? 'Launch this scraping configuration' : 'Enable this configuration first'}
                  >
                    {runningConfigId === config.id ? '⏳ Running' : '▶ Run'}
                  </button>
                  <button
                    onClick={() => handleEdit(config)}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={() => handleDelete(config.id)}
                    className="px-3 py-1 bg-red-700 text-white rounded text-sm hover:bg-red-800 transition-colors"
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>

              {/* Config Details Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <p className="text-gray-500 text-xs">Competition</p>
                  <p className="text-white font-semibold text-sm">{config.competition_name}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs">Season</p>
                  <p className="text-white font-semibold text-sm">{config.season_name || config.season_id}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs">Scrape Interval</p>
                  <p className="text-white font-semibold text-sm">{config.scrape_interval_minutes} min</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs">Provider</p>
                  <p className="text-white font-semibold text-sm">{config.provider}</p>
                </div>
              </div>

              {/* Advanced Parameters */}
              <div className="bg-dark-700 rounded p-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div>
                  <p className="text-gray-500">Look-Ahead</p>
                  <p className="text-white font-semibold">{config.look_ahead_days} days</p>
                </div>
                <div>
                  <p className="text-gray-500">Look-Back</p>
                  <p className="text-white font-semibold">{config.look_back_days} days</p>
                </div>
                <div>
                  <p className="text-gray-500">Live Window</p>
                  <p className="text-white font-semibold">{config.live_game_window_minutes} min</p>
                </div>
                <div>
                  <p className="text-gray-500">Timeout</p>
                  <p className="text-white font-semibold">{config.task_timeout_seconds / 60} min</p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
