import { useEffect, useState } from 'react';
import axios from 'axios';
import { CalendarClock, Pencil, Play, Plus, Trash2, X } from 'lucide-react';
import { API_BASE } from '../api';
import './AutomationPage.css';

const WEEKDAYS = [['M', 0], ['T', 1], ['W', 2], ['T', 3], ['F', 4], ['S', 5], ['S', 6]];
const DEFAULT_FORM = {
  name: '', description: '', competition_id: '', competition_name: '', season_id: '', season_name: '',
  provider: 'sportsdynamics', scrape_interval_minutes: 20, enabled: true,
  window_start_utc: '00:00', window_end_utc: '23:59', weekdays: [0, 1, 2, 3, 4, 5, 6],
  look_ahead_days: 7, look_back_days: 1, live_game_window_minutes: 120, task_timeout_seconds: 1800,
};

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(`${value}`.endsWith('Z') ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' });
}

function normalizeTime(value, fallback) { return String(value || fallback).slice(0, 5); }
function errorMessage(error) { return error.response?.data?.detail || error.message; }

export default function AutomationPage() {
  const [status, setStatus] = useState(null);
  const [configs, setConfigs] = useState([]);
  const [competitions, setCompetitions] = useState([]);
  const [seasons, setSeasons] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [togglingId, setTogglingId] = useState(null);
  const [runningId, setRunningId] = useState(null);

  const load = async () => {
    try {
      const [statusResponse, logsResponse, configurationsResponse, competitionsResponse] = await Promise.all([
        axios.get(`${API_BASE}/automation/status`),
        axios.get(`${API_BASE}/automation/logs?limit=10`),
        axios.get(`${API_BASE}/automation/configurations`),
        axios.get(`${API_BASE}/competitions`),
      ]);
      setStatus(statusResponse.data);
      setLogs(logsResponse.data.logs || []);
      setConfigs(configurationsResponse.data || []);
      setCompetitions(competitionsResponse.data || []);
      setError('');
    } catch (requestError) {
      setError(`Unable to load automation: ${errorMessage(requestError)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchSeasons = async competitionId => {
    if (!competitionId) { setSeasons([]); return; }
    try {
      const response = await axios.get(`${API_BASE}/competitions/${competitionId}/seasons`);
      setSeasons(response.data || []);
    } catch (requestError) {
      setSeasons([]);
      setError(`Unable to load seasons: ${errorMessage(requestError)}`);
    }
  };

  const openNew = () => {
    setEditingId(null);
    setForm({ ...DEFAULT_FORM, weekdays: [...DEFAULT_FORM.weekdays] });
    setSeasons([]);
    setMessage('');
    setEditorOpen(true);
  };

  const openEdit = configuration => {
    setEditingId(configuration.id);
    setForm({
      ...DEFAULT_FORM,
      ...configuration,
      window_start_utc: normalizeTime(configuration.window_start_utc, '00:00'),
      window_end_utc: normalizeTime(configuration.window_end_utc, '23:59'),
      weekdays: configuration.weekdays || [...DEFAULT_FORM.weekdays],
    });
    fetchSeasons(configuration.competition_id);
    setMessage('');
    setEditorOpen(true);
  };

  const updateForm = event => {
    const { name, value, type, checked } = event.target;
    setForm(current => ({ ...current, [name]: type === 'checkbox' ? checked : type === 'number' ? Number(value) : value }));
  };

  const selectCompetition = async event => {
    const competitionId = event.target.value;
    const competition = competitions.find(item => item.id === competitionId);
    setForm(current => ({ ...current, competition_id: competitionId, competition_name: competition?.name || '', season_id: '', season_name: '' }));
    await fetchSeasons(competitionId);
  };

  const selectSeason = event => {
    const season = seasons.find(item => item.id === event.target.value);
    setForm(current => ({ ...current, season_id: event.target.value, season_name: season?.name || '' }));
  };

  const toggleWeekday = day => setForm(current => ({
    ...current,
    weekdays: current.weekdays.includes(day)
      ? current.weekdays.filter(value => value !== day)
      : [...current.weekdays, day].sort((first, second) => first - second),
  }));

  const save = async event => {
    event.preventDefault();
    if (!form.weekdays.length) { setMessage('Select at least one weekday.'); return; }
    if (form.window_end_utc < form.window_start_utc) { setMessage('The end time must be after the start time.'); return; }
    setSaving(true);
    setMessage('');
    try {
      const payload = { ...form, scrape_interval_minutes: Number(form.scrape_interval_minutes), weekdays: form.weekdays };
      if (editingId) await axios.put(`${API_BASE}/automation/configurations/${editingId}`, payload);
      else await axios.post(`${API_BASE}/automation/configurations`, payload);
      setEditorOpen(false);
      setMessage(editingId ? 'Configuration updated.' : 'Configuration created.');
      await load();
    } catch (requestError) {
      setMessage(`Unable to save configuration: ${errorMessage(requestError)}`);
    } finally {
      setSaving(false);
    }
  };

  const toggle = async configuration => {
    setTogglingId(configuration.id);
    try {
      await axios.put(`${API_BASE}/automation/configurations/${configuration.id}`, { enabled: !configuration.enabled });
      await load();
    } catch (requestError) {
      setError(`Unable to update configuration: ${errorMessage(requestError)}`);
    } finally {
      setTogglingId(null);
    }
  };

  const remove = async configuration => {
    if (!window.confirm(`Delete ${configuration.name}?`)) return;
    try {
      await axios.delete(`${API_BASE}/automation/configurations/${configuration.id}`);
      setMessage('Configuration deleted.');
      await load();
    } catch (requestError) {
      setError(`Unable to delete configuration: ${errorMessage(requestError)}`);
    }
  };

  const run = async configuration => {
    setRunningId(configuration.id);
    try {
      await axios.post(`${API_BASE}/games/scrape-autonome`, { competition_id: configuration.competition_id, season_id: configuration.season_id });
      setMessage(`${configuration.name} launched.`);
      await load();
    } catch (requestError) {
      setError(`Unable to launch configuration: ${errorMessage(requestError)}`);
    } finally {
      setRunningId(null);
    }
  };

  if (loading) return <div className="physical-page physical-loading">Loading automation...</div>;

  return (
    <div className="physical-page">
      <header className="physical-hero">
        <div><p className="eyebrow physical-eyebrow">SPORTSDYNAMICS / AUTOMATION</p><h1>Automation</h1><p>Manage smart scraping rules, schedule windows, and recent execution signals.</p></div>
        <button className="physical-primary-button physical-automation-add" type="button" onClick={openNew}><Plus size={15} aria-hidden="true" /> New configuration</button>
      </header>
      {error && <div className="physical-alert">{error}</div>}
      {message && <div className="physical-result"><span>{message}</span><button type="button" onClick={() => setMessage('')} aria-label="Dismiss message"><X size={15} /></button></div>}

      <div className="physical-automation-summary">
        <div><CalendarClock size={18} aria-hidden="true" /><span><strong>{status?.is_enabled ? 'Active' : 'Inactive'}</strong><small>automation status</small></span></div>
        <div><span><strong>{configs.length}</strong><small>configurations</small></span></div>
        <div><span><strong>{configs.filter(item => item.enabled).length}</strong><small>active configurations</small></span></div>
      </div>

      <div className="physical-overview-grid">
        <section className="physical-panel">
          <div className="physical-panel-heading"><div><span className="physical-kicker">Rules</span><h2>Scheduled scraping</h2></div><span className="physical-count">{configs.length} configurations</span></div>
          <div className="physical-automation-rules">
            {configs.length ? configs.map(configuration => (
              <article className={`physical-automation-rule ${configuration.enabled ? 'is-enabled' : ''}`} key={configuration.id}>
                <div className="physical-automation-rule-top"><span className="physical-automation-rule-status" /><div><strong>{configuration.name}</strong><small>{configuration.enabled ? 'Active' : 'Paused'} · {configuration.competition_name} · {configuration.season_name || configuration.season_id}</small></div><button type="button" onClick={() => toggle(configuration)} disabled={togglingId === configuration.id} aria-label={`${configuration.enabled ? 'Disable' : 'Enable'} ${configuration.name}`} title={configuration.enabled ? 'Disable configuration' : 'Enable configuration'}><span className="physical-toggle-label">{configuration.enabled ? 'On' : 'Off'}</span></button><button type="button" onClick={() => openEdit(configuration)} aria-label={`Edit ${configuration.name}`} title="Edit configuration"><Pencil size={14} /></button><button type="button" onClick={() => remove(configuration)} aria-label={`Delete ${configuration.name}`} title="Delete configuration"><Trash2 size={14} /></button></div>
                <div className="physical-automation-rule-meta"><span>{normalizeTime(configuration.window_start_utc, '00:00')}–{normalizeTime(configuration.window_end_utc, '23:59')} UTC</span><span>Every {configuration.scrape_interval_minutes} min</span><span>{configuration.last_execution_at ? formatDate(configuration.last_execution_at) : 'Not run'}</span></div>
                <div className="physical-automation-days">{WEEKDAYS.map(([label, day]) => <i className={(configuration.weekdays || []).includes(day) ? 'is-selected' : ''} key={day}>{label}</i>)}</div>
                <div className="physical-automation-rule-actions"><button type="button" onClick={() => run(configuration)} disabled={!configuration.enabled || runningId === configuration.id}><Play size={12} /> {runningId === configuration.id ? 'Running' : 'Run now'}</button><span>{configuration.enabled ? configuration.next_refresh_at ? `Next ${formatDate(configuration.next_refresh_at)}` : 'Waiting for Beat' : 'Disabled'}</span></div>
              </article>
            )) : <div className="physical-empty">No automation configurations yet.</div>}
          </div>
        </section>

        <section className="physical-panel">
          <div className="physical-panel-heading"><div><span className="physical-kicker">Execution history</span><h2>Latest automation logs</h2></div><span className="physical-count">10 latest</span></div>
          <div className="physical-automation-runs">{logs.length ? logs.map(log => <div className="physical-automation-run" key={log.id}><span className={`physical-run-status ${log.status}`}>{log.status}</span><div><strong>{log.configuration_name || log.competition_name}</strong><small>{formatDate(log.executed_at)}</small></div><em>{log.games_count || 0} games</em>{log.error_message && <p>{log.error_message}</p>}</div>) : <div className="physical-empty">No automation logs recorded yet.</div>}</div>
        </section>
      </div>

      {editorOpen && <div className="physical-offcanvas-backdrop" onClick={() => !saving && setEditorOpen(false)}><aside className="physical-automation-offcanvas" onClick={event => event.stopPropagation()}><div className="physical-panel-heading"><div><span className="physical-kicker">Configuration editor</span><h2>{editingId ? 'Edit configuration' : 'New configuration'}</h2></div><button type="button" className="physical-offcanvas-close" onClick={() => !saving && setEditorOpen(false)} aria-label="Close editor"><X size={18} /></button></div><form className="physical-config-form" onSubmit={save}>
+        <label>Name<input name="name" value={form.name} onChange={updateForm} required maxLength="255" /></label>
+        <label>Description<input name="description" value={form.description || ''} onChange={updateForm} /></label>
        <div className="physical-field-row"><label>Competition<select name="competition_id" value={form.competition_id} onChange={selectCompetition} required><option value="">Select a competition</option>{competitions.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Season<select name="season_id" value={form.season_id} onChange={selectSeason} required disabled={!form.competition_id}><option value="">Select a season</option>{seasons.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label></div>
        <div className="physical-field-row"><label>Start (UTC)<input type="time" name="window_start_utc" value={form.window_start_utc} onChange={updateForm} required /></label><label>End (UTC)<input type="time" name="window_end_utc" value={form.window_end_utc} onChange={updateForm} required /></label></div>
        <fieldset><legend>Weekdays (UTC)</legend><div className="physical-weekday-picker">{WEEKDAYS.map(([label, day]) => <button type="button" className={form.weekdays.includes(day) ? 'is-selected' : ''} onClick={() => toggleWeekday(day)} key={day}>{label}</button>)}</div></fieldset>
        <div className="physical-field-row"><label>Interval (minutes)<input type="number" min="1" name="scrape_interval_minutes" value={form.scrape_interval_minutes} onChange={updateForm} required /></label><label>Provider<select name="provider" value={form.provider} onChange={updateForm}><option value="sportsdynamics">SportsDynamics</option><option value="perform">Perform</option><option value="secondspectrum">SecondSpectrum</option></select></label></div>
        <div className="physical-field-row"><label>Look ahead (days)<input type="number" min="1" name="look_ahead_days" value={form.look_ahead_days} onChange={updateForm} required /></label><label>Look back (days)<input type="number" min="0" name="look_back_days" value={form.look_back_days} onChange={updateForm} required /></label></div>
        <div className="physical-field-row"><label>Live window (minutes)<input type="number" min="1" name="live_game_window_minutes" value={form.live_game_window_minutes} onChange={updateForm} required /></label><label>Timeout (seconds)<input type="number" min="60" name="task_timeout_seconds" value={form.task_timeout_seconds} onChange={updateForm} required /></label></div>
        <label className="physical-toggle"><input type="checkbox" name="enabled" checked={form.enabled} onChange={updateForm} /><span><strong>Configuration enabled</strong><small>Include this rule in the automation cycle.</small></span><i /></label>
        {message && <p className="physical-form-message">{message}</p>}
        <div className="physical-offcanvas-actions"><button className="physical-primary-button" type="submit" disabled={saving}>{saving ? 'Saving...' : editingId ? 'Save changes' : 'Create configuration'}</button><button type="button" onClick={() => !saving && setEditorOpen(false)}>Cancel</button></div>
      </form></aside></div>}
    </div>
  );
}
