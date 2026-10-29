import { useEffect, useState } from "react";
import axios from "axios";
import { CheckSquare, Copy, Eraser, Save } from "lucide-react";
import { API_BASE } from "../api";

const METRICS = [
  ["distanceTotal", "Distance total"],
  ["distancePerMin", "Distance / min"],
  ["distanceZ5Rel", "Distance Z5 relative"],
  ["distanceZ6Rel", "Distance Z6 relative"],
  ["distanceZ5Abs", "Distance Z5 absolute"],
  ["distanceZ6Abs", "Distance Z6 absolute"],
  ["entriesZ5Abs", "Entries Z5 absolute"],
  ["entriesZ6Abs", "Entries Z6 absolute"],
  ["accelerations", "Accelerations"],
  ["decelerations", "Decelerations"],
  ["totalTime", "Total time"],
  ["maxSpeed", "Max speed"],
  ["distanceZ1R", "Distance Z1 relative"],
  ["distanceZ1A", "Distance Z1 absolute"],
  ["distanceZ2R", "Distance Z2 relative"],
  ["distanceZ2A", "Distance Z2 absolute"],
  ["distanceZ3R", "Distance Z3 relative"],
  ["distanceZ3A", "Distance Z3 absolute"],
  ["distanceZ4R", "Distance Z4 relative"],
  ["distanceZ4A", "Distance Z4 absolute"],
];

function playerName(player) {
  return (
    player.display_name ||
    `${player.first_name || ""} ${player.last_name || ""}`.trim() ||
    "Joueur sans nom"
  );
}

function sessionName(session) {
  return `${session.activity_name || "Session sans nom"} · ${String(session.session_date || "").slice(0, 10)}`;
}

export default function PhysicalDataEditorPage({ initialSessionId = "", initialPlayerId = "" }) {
  const [sessions, setSessions] = useState([]);
  const [players, setPlayers] = useState([]);
  const [sessionId, setSessionId] = useState("");
  const [playerId, setPlayerId] = useState("");
  const [drills, setDrills] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [sourcePlayerId, setSourcePlayerId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState({});

  useEffect(() => {
    Promise.all([
      axios.get(`${API_BASE}/physical/sessions?limit=500`),
      axios.get(`${API_BASE}/physical/players/all`),
    ])
      .then(([sessionResponse, playerResponse]) => {
        const nextSessions = sessionResponse.data || [];
        const nextPlayers = playerResponse.data || [];
        setSessions(nextSessions);
        setPlayers(nextPlayers);
        setSessionId(
          nextSessions.some((session) => session.id === initialSessionId)
            ? initialSessionId
            : nextSessions[0]?.id || "",
        );
        setPlayerId(
          nextPlayers.some((player) => player.id === initialPlayerId)
            ? initialPlayerId
            : nextPlayers[0]?.id || "",
        );
      })
      .catch((error) =>
        setMessage(error.response?.data?.detail || error.message),
      )
      .finally(() => setLoading(false));
  }, [initialPlayerId, initialSessionId]);

  const loadGrid = async () => {
    if (!sessionId || !playerId) return;
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/physical/editor/catalog`, {
        params: { session_id: sessionId, player_id: playerId },
      });
      setDrills(response.data.drills || []);
      setSelected(new Set());
      setPending({});
      setMessage("");
    } catch (error) {
      setMessage(error.response?.data?.detail || error.message);
      setDrills([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGrid();
  }, [sessionId, playerId]);

  const updateValue = (drillId, metric, rawValue) => {
    const value = rawValue === "" ? null : Number(rawValue);
    if (rawValue !== "" && Number.isNaN(value)) return;
    setPending((current) => ({
      ...current,
      [drillId]: { ...(current[drillId] || {}), [metric]: value },
    }));
    setDrills((current) =>
      current.map((drill) =>
        drill.id === drillId
          ? { ...drill, values: { ...drill.values, [metric]: value } }
          : drill,
      ),
    );
  };

  const saveAll = async () => {
    const rows = Object.entries(pending).map(
      ([drill_metadata_id, metrics]) => ({ drill_metadata_id, metrics }),
    );
    if (!rows.length) return;
    setSaving(true);
    try {
      const response = await axios.post(`${API_BASE}/physical/editor/save`, {
        session_id: sessionId,
        player_id: playerId,
        rows,
      });
      setMessage(`${response.data.updated} ligne(s) d’exercice enregistrée(s).`);
      await loadGrid();
    } catch (error) {
      setMessage(error.response?.data?.detail || error.message);
    } finally {
      setSaving(false);
    }
  };

  const bulk = async (action) => {
    if (!selected.size) return;
    setSaving(true);
    try {
      const response = await axios.post(`${API_BASE}/physical/editor/bulk`, {
        session_id: sessionId,
        player_id: playerId,
        drill_metadata_ids: [...selected],
        action,
        source_player_id: action === "copy" ? sourcePlayerId : undefined,
      });
      const preparedRows = response.data.rows || [];
      const preparedById = Object.fromEntries(
        preparedRows.map((row) => [row.drill_metadata_id, row.metrics]),
      );
      setDrills((current) =>
        current.map((drill) =>
          preparedById[drill.id]
            ? {
                ...drill,
                values: { ...drill.values, ...preparedById[drill.id] },
              }
            : drill,
        ),
      );
      setPending((current) =>
        preparedRows.reduce(
          (next, row) => ({
            ...next,
            [row.drill_metadata_id]: {
              ...(next[row.drill_metadata_id] || {}),
              ...row.metrics,
            },
          }),
          current,
        ),
      );
      setMessage(
        `${response.data.updated} ligne(s) d’exercice préparée(s). Enregistrez pour appliquer les changements.`,
      );
    } catch (error) {
      setMessage(error.response?.data?.detail || error.message);
    } finally {
      setSaving(false);
    }
  };

  const clearSelected = () => {
    if (!selected.size) return;
    const emptyMetrics = Object.fromEntries(
      METRICS.map(([metric]) => [metric, null]),
    );
    setDrills((current) =>
      current.map((drill) =>
        selected.has(drill.id)
          ? { ...drill, values: { ...drill.values, ...emptyMetrics } }
          : drill,
      ),
    );
    setPending((current) =>
      [...selected].reduce(
        (next, drillId) => ({
          ...next,
          [drillId]: { ...(next[drillId] || {}), ...emptyMetrics },
        }),
        current,
      ),
    );
    setMessage(
      `${selected.size} ligne(s) d’exercice effacée(s) localement. Enregistrez pour confirmer le nettoyage.`,
    );
  };

  const toggleAll = (checked) =>
    setSelected(checked ? new Set(drills.map((drill) => drill.id)) : new Set());
  const toggleDrill = (id) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (loading && !drills.length)
    return (
      <div className="physical-page physical-loading">
        Chargement de l’éditeur de données physiques...
      </div>
    );
  return (
    <div className="physical-page physical-editor-page">
      <header className="physical-hero">
        <div>
          <p className="eyebrow physical-eyebrow">
            PHYSICALDATA / ÉDITEUR MANUEL
          </p>
          <h1>Éditeur manuel des données</h1>
          <p>
            Modifiez un sous-ensemble stable de métriques sans altérer les
            données STATSports importées.
          </p>
        </div>
        <div className="physical-live">
          <span /> {selected.size} exercice(s) sélectionné(s)
        </div>
      </header>
      <section className="physical-panel physical-editor-controls">
        <div className="physical-editor-selectors">
          <label>
            Session
            <select
              value={sessionId}
              onChange={(event) => setSessionId(event.target.value)}
            >
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>
                  {sessionName(session)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Joueur cible
            <select
              value={playerId}
              onChange={(event) => setPlayerId(event.target.value)}
            >
              {players.map((player) => (
                <option key={player.id} value={player.id}>
                  {playerName(player)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source de copie
            <select
              value={sourcePlayerId}
              onChange={(event) => setSourcePlayerId(event.target.value)}
            >
              <option value="">Sélectionner une source</option>
              {players
                .filter((player) => player.id !== playerId)
                .map((player) => (
                  <option key={player.id} value={player.id}>
                    {playerName(player)}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <div className="physical-editor-actions">
          <button
            type="button"
            onClick={() => toggleAll(selected.size !== drills.length)}
          >
            <CheckSquare size={15} />{" "}
            {selected.size === drills.length && drills.length
              ? "Tout désélectionner"
              : "Tout sélectionner"}
          </button>
          <button
            type="button"
            disabled={!selected.size || saving}
            onClick={clearSelected}
          >
            <Eraser size={15} /> Effacer les valeurs sélectionnées
          </button>
          <button
            type="button"
            disabled={!selected.size || !sourcePlayerId || saving}
            onClick={() => bulk("copy")}
          >
            <Copy size={15} /> Copier les valeurs source
          </button>
          <button
            type="button"
            disabled={!selected.size || saving}
            onClick={() => bulk("average")}
          >
            <Save size={15} /> Calculer la moyenne des joueurs présents
          </button>
          <button
            type="button"
            disabled={!Object.keys(pending).length || saving}
            onClick={saveAll}
          >
            <Save size={15} /> Enregistrer les modifications
          </button>
        </div>
      </section>
      {message && (
        <div className="physical-result">
          <span>{message}</span>
        </div>
      )}
      <section className="physical-panel">
        <div className="physical-panel-heading">
          <div>
            <span className="physical-kicker">Sous-ensemble modifiable</span>
            <h2>Métriques des exercices</h2>
          </div>
          <span className="physical-count">{drills.length} ligne(s)</span>
        </div>
        {drills.length ? (
          <div className="physical-editor-table">
            <div className="physical-editor-drill-column">
              <div className="physical-editor-drill-header">Exercice</div>
              {drills.map((drill) => (
                <label className="physical-editor-drill" key={drill.id}>
                  <input
                    type="checkbox"
                    checked={selected.has(drill.id)}
                    onChange={() => toggleDrill(drill.id)}
                  />
                  <strong>{drill.drill_name || "Unnamed drill"}</strong>
                  <small>
                    {[
                      drill.primary_label,
                      drill.secondary_label,
                      drill.tertiary_label,
                    ]
                      .filter(Boolean)
                      .join(" · ") ||
                      drill.session_type ||
                      "No label"}
                  </small>
                </label>
              ))}
            </div>
            <div className="physical-editor-metrics-scroll">
              <div className="physical-editor-metrics">
                <div className="physical-editor-metric-row physical-editor-header">
                  {METRICS.map(([, label]) => (
                    <span key={label}>
                      {label.replace(/\s+(absolute|relative)$/i, "")}
                      {/\s+(absolute|relative)$/i.test(label) && (
                        <small>
                          {label.match(/(absolute|relative)$/i)?.[1]}
                        </small>
                      )}
                    </span>
                  ))}
                </div>
                {drills.map((drill) => (
                  <div className="physical-editor-metric-row" key={drill.id}>
                    {METRICS.map(([metric]) => (
                      <input
                        key={metric}
                        type="number"
                        step="any"
                        value={drill.values[metric] ?? ""}
                        onChange={(event) =>
                          updateValue(drill.id, metric, event.target.value)
                        }
                        disabled={saving}
                        aria-label={`${drill.drill_name || "Drill"} ${metric}`}
                      />
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="physical-empty">
            No editable drill metadata exists for this session.
          </div>
        )}
      </section>
    </div>
  );
}
