import { useEffect, useState } from 'react';
import axios from 'axios';
import { CalendarClock, Pencil, Play, Plus, Trash2, X } from 'lucide-react';
import { API_BASE } from '../api';
import './AutomationPage.css';

const WEEKDAYS = [['L', 0], ['M', 1], ['M', 2], ['J', 3], ['V', 4], ['S', 5], ['D', 6]];
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
      setError(`Impossible de charger l’automatisation : ${errorMessage(requestError)}`);
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
      setError(`Impossible de charger les saisons : ${errorMessage(requestError)}`);
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
    if (!form.weekdays.length) { setMessage('Sélectionnez au moins un jour.'); return; }
    if (form.window_end_utc < form.window_start_utc) { setMessage('L’heure de fin doit être postérieure à l’heure de début.'); return; }
    setSaving(true);
    setMessage('');
    try {
      const payload = { ...form, scrape_interval_minutes: Number(form.scrape_interval_minutes), weekdays: form.weekdays };
      if (editingId) await axios.put(`${API_BASE}/automation/configurations/${editingId}`, payload);
      else await axios.post(`${API_BASE}/automation/configurations`, payload);
      setEditorOpen(false);
      setMessage(editingId ? 'Configuration mise à jour.' : 'Configuration créée.');
      await load();
    } catch (requestError) {
      setMessage(`Impossible d’enregistrer la configuration : ${errorMessage(requestError)}`);
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
      setError(`Impossible de mettre à jour la configuration : ${errorMessage(requestError)}`);
    } finally {
      setTogglingId(null);
    }
  };

  const remove = async configuration => {
    if (!window.confirm(`Supprimer ${configuration.name} ?`)) return;
    try {
      await axios.delete(`${API_BASE}/automation/configurations/${configuration.id}`);
      setMessage('Configuration supprimée.');
      await load();
    } catch (requestError) {
      setError(`Impossible de supprimer la configuration : ${errorMessage(requestError)}`);
    }
  };

  const run = async configuration => {
    setRunningId(configuration.id);
    try {
      await axios.post(`${API_BASE}/games/scrape-autonome`, { competition_id: configuration.competition_id, season_id: configuration.season_id });
      setMessage(`${configuration.name} lancée.`);
      await load();
    } catch (requestError) {
      setError(`Impossible de lancer la configuration : ${errorMessage(requestError)}`);
    } finally {
      setRunningId(null);
    }
  };

  if (loading) return <div className="physical-page physical-loading">Chargement de l’automatisation...</div>;

  return (
    <div className="physical-page">
      <header className="physical-hero">
        <div><p className="eyebrow physical-eyebrow">ESPACE DE TRAVAIL / AUTOMATISATION</p><h1>Automatisation</h1><p>Gérez les règles de collecte, les plages horaires et les dernières exécutions.</p></div>
        <button className="physical-primary-button physical-automation-add" type="button" onClick={openNew}><Plus size={15} aria-hidden="true" /> Nouvelle configuration</button>
      </header>
      {error && <div className="physical-alert">{error}</div>}
      {message && <div className="physical-result"><span>{message}</span><button type="button" onClick={() => setMessage('')} aria-label="Dismiss message"><X size={15} /></button></div>}

      <div className="physical-automation-summary">
        <div><CalendarClock size={18} aria-hidden="true" /><span><strong>{status?.is_enabled ? 'Active' : 'Inactive'}</strong><small>état de l’automatisation</small></span></div>
        <div><span><strong>{configs.length}</strong><small>configurations</small></span></div>
        <div><span><strong>{configs.filter(item => item.enabled).length}</strong><small>configurations actives</small></span></div>
      </div>

      <div className="physical-overview-grid">
        <section className="physical-panel">
          <div className="physical-panel-heading"><div><span className="physical-kicker">Règles</span><h2>Collectes planifiées</h2></div><span className="physical-count">{configs.length} configurations</span></div>
          <div className="physical-automation-rules">
            {configs.length ? configs.map(configuration => (
              <article className={`physical-automation-rule ${configuration.enabled ? 'is-enabled' : ''}`} key={configuration.id}>
                <div className="physical-automation-rule-top"><span className="physical-automation-rule-status" /><div><strong>{configuration.name}</strong><small>{configuration.enabled ? 'Active' : 'En pause'} · {configuration.competition_name} · {configuration.season_name || configuration.season_id}</small></div><button type="button" onClick={() => toggle(configuration)} disabled={togglingId === configuration.id} aria-label={`${configuration.enabled ? 'Désactiver' : 'Activer'} ${configuration.name}`} title={configuration.enabled ? 'Désactiver la configuration' : 'Activer la configuration'}><span className="physical-toggle-label">{configuration.enabled ? 'Actif' : 'Inactif'}</span></button><button type="button" onClick={() => openEdit(configuration)} aria-label={`Modifier ${configuration.name}`} title="Modifier la configuration"><Pencil size={14} /></button><button type="button" onClick={() => remove(configuration)} aria-label={`Supprimer ${configuration.name}`} title="Supprimer la configuration"><Trash2 size={14} /></button></div>
                <div className="physical-automation-rule-meta"><span>{normalizeTime(configuration.window_start_utc, '00:00')}–{normalizeTime(configuration.window_end_utc, '23:59')} UTC</span><span>Toutes les {configuration.scrape_interval_minutes} min</span><span>{configuration.last_execution_at ? formatDate(configuration.last_execution_at) : 'Jamais exécutée'}</span></div>
                <div className="physical-automation-days">{WEEKDAYS.map(([label, day]) => <i className={(configuration.weekdays || []).includes(day) ? 'is-selected' : ''} key={day}>{label}</i>)}</div>
                <div className="physical-automation-rule-actions"><button type="button" onClick={() => run(configuration)} disabled={!configuration.enabled || runningId === configuration.id}><Play size={12} /> {runningId === configuration.id ? 'En cours' : 'Lancer maintenant'}</button><span>{configuration.enabled ? configuration.next_refresh_at ? `Prochaine : ${formatDate(configuration.next_refresh_at)}` : 'En attente du planificateur' : 'Désactivée'}</span></div>
              </article>
            )) : <div className="physical-empty">Aucune configuration d’automatisation.</div>}
          </div>
        </section>

        <section className="physical-panel">
          <div className="physical-panel-heading"><div><span className="physical-kicker">Historique des exécutions</span><h2>Derniers journaux d’automatisation</h2></div><span className="physical-count">10 derniers</span></div>
          <div className="physical-automation-runs">{logs.length ? logs.map(log => <div className="physical-automation-run" key={log.id}><span className={`physical-run-status ${log.status}`}>{log.status}</span><div><strong>{log.configuration_name || log.competition_name}</strong><small>{formatDate(log.executed_at)}</small></div><em>{log.games_count || 0} matchs</em>{log.error_message && <p>{log.error_message}</p>}</div>) : <div className="physical-empty">Aucun journal d’automatisation.</div>}</div>
        </section>
      </div>

      {editorOpen && <div className="physical-offcanvas-backdrop" onClick={() => !saving && setEditorOpen(false)}><aside className="physical-automation-offcanvas" onClick={event => event.stopPropagation()}><div className="physical-panel-heading"><div><span className="physical-kicker">ÉDITEUR DE CONFIGURATION</span><h2>{editingId ? 'Modifier la configuration' : 'Nouvelle configuration'}</h2></div><button type="button" className="physical-offcanvas-close" onClick={() => !saving && setEditorOpen(false)} aria-label="Fermer l’éditeur"><X size={18} /></button></div><form className="physical-config-form" onSubmit={save}>
        <label>Nom<input name="name" value={form.name} onChange={updateForm} required maxLength="255" /></label>
        <label>Description<input name="description" value={form.description || ''} onChange={updateForm} /></label>
        <div className="physical-field-row"><label>Compétition<select name="competition_id" value={form.competition_id} onChange={selectCompetition} required><option value="">Sélectionner une compétition</option>{competitions.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Saison<select name="season_id" value={form.season_id} onChange={selectSeason} required disabled={!form.competition_id}><option value="">Sélectionner une saison</option>{seasons.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label></div>
        <div className="physical-field-row"><label>Début (UTC)<input type="time" name="window_start_utc" value={form.window_start_utc} onChange={updateForm} required /></label><label>Fin (UTC)<input type="time" name="window_end_utc" value={form.window_end_utc} onChange={updateForm} required /></label></div>
        <fieldset><legend>Jours actifs (UTC)</legend><div className="physical-weekday-picker">{WEEKDAYS.map(([label, day]) => <button type="button" className={form.weekdays.includes(day) ? 'is-selected' : ''} onClick={() => toggleWeekday(day)} key={day}>{label}</button>)}</div></fieldset>
        <div className="physical-field-row"><label>Intervalle (minutes)<input type="number" min="1" name="scrape_interval_minutes" value={form.scrape_interval_minutes} onChange={updateForm} required /></label><label>Fournisseur<select name="provider" value={form.provider} onChange={updateForm}><option value="sportsdynamics">SportsDynamics</option><option value="perform">Perform</option><option value="secondspectrum">SecondSpectrum</option></select></label></div>
        <div className="physical-field-row"><label>Anticipation (jours)<input type="number" min="1" name="look_ahead_days" value={form.look_ahead_days} onChange={updateForm} required /></label><label>Historique (jours)<input type="number" min="0" name="look_back_days" value={form.look_back_days} onChange={updateForm} required /></label></div>
        <div className="physical-field-row"><label>Fenêtre live (minutes)<input type="number" min="1" name="live_game_window_minutes" value={form.live_game_window_minutes} onChange={updateForm} required /></label><label>Délai maximal (secondes)<input type="number" min="60" name="task_timeout_seconds" value={form.task_timeout_seconds} onChange={updateForm} required /></label></div>
        <label className="physical-toggle"><input type="checkbox" name="enabled" checked={form.enabled} onChange={updateForm} /><span><strong>Configuration active</strong><small>Inclure cette règle dans le cycle d’automatisation.</small></span><i /></label>
        {message && <p className="physical-form-message">{message}</p>}
        <div className="physical-offcanvas-actions"><button className="physical-primary-button" type="submit" disabled={saving}>{saving ? 'Enregistrement...' : editingId ? 'Enregistrer' : 'Créer la configuration'}</button><button type="button" onClick={() => !saving && setEditorOpen(false)}>Annuler</button></div>
      </form></aside></div>}
    </div>
  );
}
