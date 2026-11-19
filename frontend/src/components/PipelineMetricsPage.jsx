import { useEffect, useState } from 'react'
import axios from 'axios'
import { Activity, Clock3, Database, RefreshCw, TriangleAlert } from 'lucide-react'
import './PipelineMetricsPage.css'

const ENTITY_LABELS = {
  physical: 'PhysicalData',
  tactical: 'TacticalData',
}
const RANGES = [7, 30, 90]
const SERIES_COLORS = {
  physical: 'physical',
  tactical: 'tactical',
  physicalUpdated: 'physical-updated',
  tacticalDeleted: 'tactical-deleted',
}

function numberValue(value) {
  return Number(value) || 0
}

function formatNumber(value) {
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(numberValue(value))
}

function formatDuration(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  const seconds = Math.max(0, Math.round(Number(value)))
  if (seconds < 60) return `${seconds} s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ${seconds % 60} s`
  return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`
}

function formatDateKey(value, days) {
  const date = new Date(`${value}T12:00:00Z`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('fr-FR', days <= 7
    ? { weekday: 'short', timeZone: 'Europe/Paris' }
    : { day: '2-digit', month: '2-digit', timeZone: 'Europe/Paris' })
}

function formatTimestamp(value) {
  if (!value) return 'En cours'
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return 'Date indisponible'
  return date.toLocaleString('fr-FR', {
    timeZone: 'Europe/Paris',
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

function statusLabel(status) {
  return ({
    pending: 'En attente',
    running: 'En cours',
    completed: 'Terminée',
    success: 'Terminée',
    partial: 'Partielle',
    failed: 'Échec',
    error: 'Échec',
    skipped: 'Ignorée',
  })[String(status || '').toLowerCase()] || status || 'Inconnu'
}

function getDailyValue(point, series) {
  const daily = point[series.entity]
  if (!daily) return series.key === 'average_duration_seconds' ? null : 0
  if (series.key === 'physical_volume') {
    return numberValue(daily.inserted_items) + numberValue(daily.updated_items)
  }
  return daily[series.key] === null || daily[series.key] === undefined
    ? null
    : numberValue(daily[series.key])
}

function buildTimeline(entities, days) {
  const dailyByEntity = Object.fromEntries(Object.entries(entities).map(([entity, data]) => [
    entity,
    new Map((data.daily || []).map(day => [String(day.date).slice(0, 10), day])),
  ]))
  const today = new Date()
  today.setUTCHours(0, 0, 0, 0)
  today.setUTCDate(today.getUTCDate() - days + 1)

  return Array.from({ length: days }, (_, index) => {
    const date = new Date(today)
    date.setUTCDate(today.getUTCDate() + index)
    const key = date.toISOString().slice(0, 10)
    return {
      date: key,
      ...Object.fromEntries(Object.entries(dailyByEntity).map(([entity, rows]) => [entity, rows.get(key) || null])),
    }
  })
}

function TrendChart({ title, description, points, series, days, formatter = formatNumber }) {
  const width = 640
  const height = 220
  const left = 46
  const right = 14
  const top = 14
  const bottom = 34
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const values = points.flatMap(point => series.map(item => getDailyValue(point, item)))
    .filter(value => value !== null && Number.isFinite(value))
  const maximum = Math.max(1, ...values)
  const hasData = series.some(item => points.some(point => point[item.entity]))
  const yPosition = value => top + plotHeight - (value / maximum) * plotHeight
  const xPosition = index => left + (points.length <= 1 ? plotWidth / 2 : index * plotWidth / (points.length - 1))
  const tickIndexes = [...new Set([0, Math.floor((points.length - 1) / 3), Math.floor(2 * (points.length - 1) / 3), points.length - 1])]

  function pathFor(item) {
    const segments = []
    let segment = []
    points.forEach((point, index) => {
      const value = getDailyValue(point, item)
      if (value === null) {
        if (segment.length) segments.push(segment)
        segment = []
      } else {
        segment.push(`${index === 0 || !segment.length ? 'M' : 'L'} ${xPosition(index)} ${yPosition(value)}`)
      }
    })
    if (segment.length) segments.push(segment)
    return segments.map(path => path.join(' '))
  }

  return (
    <section className="pipeline-chart-panel" aria-label={title}>
      <div className="pipeline-chart-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>
      {!hasData ? (
        <div className="pipeline-chart-empty">Aucune donnée sur cette période.</div>
      ) : (
        <>
          <svg className="pipeline-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
            <title>{title}</title>
            <desc>{description}</desc>
            {[0, 0.5, 1].map(fraction => {
              const value = maximum * fraction
              const y = yPosition(value)
              return (
                <g key={fraction}>
                  <line className="pipeline-chart-gridline" x1={left} y1={y} x2={width - right} y2={y} />
                  <text className="pipeline-chart-axis-label" x={left - 8} y={y + 4} textAnchor="end">{formatter(value)}</text>
                </g>
              )
            })}
            {tickIndexes.map(index => (
              <text className="pipeline-chart-axis-label" key={index} x={xPosition(index)} y={height - 10} textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}>
                {formatDateKey(points[index].date, days)}
              </text>
            ))}
            {series.map(item => pathFor(item).map((path, index) => (
              <path className={`pipeline-chart-line series-${SERIES_COLORS[item.id] || item.entity}`} d={path} key={`${item.id}-${index}`} />
            )))}
          </svg>
          <div className="pipeline-chart-legend">
            {series.map(item => (
              <span key={item.id}>
                <i className={`series-marker series-${SERIES_COLORS[item.id] || item.entity}`} aria-hidden="true" />
                {item.label}
              </span>
            ))}
          </div>
        </>
      )}
    </section>
  )
}

function Metric({ icon: Icon, label, value, detail, tone }) {
  return (
    <div className={`pipeline-metric tone-${tone}`}>
      <div className="pipeline-metric-label"><Icon size={16} aria-hidden="true" /><span>{label}</span></div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  )
}

export default function PipelineMetricsPage() {
  const [days, setDays] = useState(30)
  const [refreshKey, setRefreshKey] = useState(0)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    axios.get('/api/metrics/pipelines', { params: { days }, signal: controller.signal })
      .then(response => {
        setData(response.data)
        setUpdatedAt(new Date())
      })
      .catch(requestError => {
        if (!controller.signal.aborted) setError(requestError.response?.data?.detail || 'Les données de supervision sont momentanément indisponibles.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [days, refreshKey])

  const entities = data?.entities || {}
  const visibleEntities = Object.keys(ENTITY_LABELS).filter(entity => entities[entity])
  const timeline = buildTimeline(entities, days)
  const totals = visibleEntities.reduce((result, entity) => {
    const metrics = entities[entity].metrics || {}
    for (const key of ['runs', 'finished_runs', 'error_runs']) {
      result[key] += numberValue(metrics[key])
    }
    result.duration += numberValue(metrics.average_duration_seconds) * numberValue(metrics.finished_runs)
    return result
  }, { runs: 0, finished_runs: 0, error_runs: 0, duration: 0 })
  const averageDuration = totals.finished_runs ? totals.duration / totals.finished_runs : null
  const recentRuns = visibleEntities.flatMap(entity => (entities[entity].recent_runs || []).map(run => ({ ...run, entity })))
    .sort((left, right) => new Date(right.started_at || right.created_at || 0) - new Date(left.started_at || left.created_at || 0))
  const commonSeries = visibleEntities.map(entity => ({ id: entity, entity, key: 'runs', label: ENTITY_LABELS[entity] }))
  const durationSeries = visibleEntities.map(entity => ({ id: entity, entity, key: 'average_duration_seconds', label: ENTITY_LABELS[entity] }))
  const errorSeries = visibleEntities.map(entity => ({ id: entity, entity, key: 'error_runs', label: ENTITY_LABELS[entity] }))
  const physicalVolumeSeries = entities.physical ? [
    { id: 'physical', entity: 'physical', key: 'inserted_items', label: 'Activités insérées' },
    { id: 'physicalUpdated', entity: 'physical', key: 'updated_items', label: 'Activités mises à jour' },
  ] : []
  const tacticalVolumeSeries = entities.tactical ? [
    { id: 'tactical', entity: 'tactical', key: 'inserted_rows', label: 'Lignes insérées' },
    { id: 'tacticalDeleted', entity: 'tactical', key: 'deleted_rows', label: 'Lignes supprimées' },
  ] : []

  return (
    <div className="pipeline-page">
      <header className="pipeline-heading">
        <div>
          <p className="eyebrow">OBSERVABILITÉ / COLLECTES</p>
          <h1>Supervision des pipelines</h1>
          <p>Exécutions, durées et volumes enregistrés pour les entités auxquelles vous avez accès.</p>
        </div>
        <button className="pipeline-refresh" type="button" onClick={() => setRefreshKey(value => value + 1)} disabled={loading}>
          <RefreshCw size={16} aria-hidden="true" />
          Actualiser
        </button>
      </header>

      <div className="pipeline-toolbar">
        <div className="pipeline-range" role="group" aria-label="Période affichée">
          {RANGES.map(range => (
            <button key={range} type="button" aria-pressed={days === range} onClick={() => setDays(range)}>
              {range} jours
            </button>
          ))}
        </div>
        <span className="pipeline-updated">{updatedAt ? `Actualisé à ${updatedAt.toLocaleTimeString('fr-FR', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit' })}` : ' '}</span>
      </div>

      {error && (
        <div className="pipeline-error" role="alert">
          <TriangleAlert size={18} aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={() => setRefreshKey(value => value + 1)}>Réessayer</button>
        </div>
      )}

      {loading && !data ? (
        <div className="pipeline-state" role="status">Chargement des métriques…</div>
      ) : !error && visibleEntities.length === 0 ? (
        <div className="pipeline-state">Aucune entité de données n’est accessible à ce compte.</div>
      ) : !error && (
        <>
          <section className="pipeline-overview-metrics" aria-label="Indicateurs de synthèse">
            <Metric icon={Activity} label="Runs" value={formatNumber(totals.runs)} detail={`sur ${days} jours`} tone="physical" />
            <Metric icon={Clock3} label="Durée moyenne" value={formatDuration(averageDuration)} detail={`${formatNumber(totals.finished_runs)} runs terminés`} tone="tactical" />
            <Metric icon={Database} label="Runs en échec" value={formatNumber(totals.error_runs)} detail="échoués ou partiels" tone="danger" />
          </section>

          {visibleEntities.length === 2 && (
            <p className="pipeline-unit-note">Les volumes PhysicalData comptent des activités ; les volumes TacticalData comptent des lignes de base de données. Ils sont présentés séparément.</p>
          )}

          <section className="pipeline-chart-grid" aria-label="Tendances des pipelines">
            <TrendChart title="Runs par jour" description="Nombre d’exécutions par entité et par jour." points={timeline} series={commonSeries} days={days} />
            <TrendChart title="Durée moyenne" description="Durée moyenne des exécutions terminées, en secondes." points={timeline} series={durationSeries} days={days} formatter={formatDuration} />
            {entities.physical && <TrendChart title="Activités PhysicalData" description="Activités insérées et mises à jour par jour." points={timeline} series={physicalVolumeSeries} days={days} />}
            {entities.tactical && <TrendChart title="Écritures TacticalData" description="Lignes insérées et supprimées dans la base par jour." points={timeline} series={tacticalVolumeSeries} days={days} />}
            <TrendChart title="Runs en échec ou partiels" description="Nombre de runs en échec ou partiels par jour." points={timeline} series={errorSeries} days={days} />
          </section>

          <section className="pipeline-recent-section">
            <div className="pipeline-section-heading">
              <div><h2>Runs récents</h2><p>Dernières exécutions enregistrées sur la période.</p></div>
            </div>
            {recentRuns.length === 0 ? (
              <p className="pipeline-empty">Aucun run trouvé pour cette période.</p>
            ) : (
              <div className="pipeline-table-wrap">
                <table className="pipeline-table">
                  <thead><tr><th>Entité</th><th>Workflow</th><th>Début</th><th>Durée</th><th>Éléments</th><th>Insertions</th><th>Mises à jour</th><th>Erreurs</th><th>État</th></tr></thead>
                  <tbody>
                    {recentRuns.map(run => {
                      const items = run.entity === 'physical' ? run.found : run.processed_items
                      const inserted = run.entity === 'physical' ? run.inserted_items : run.inserted_rows
                      const updated = run.entity === 'physical' ? run.updated_items : run.updated_rows
                      return (
                        <tr key={`${run.entity}-${run.id}`}>
                          <td><span className={`pipeline-entity-tag entity-${run.entity}`}>{ENTITY_LABELS[run.entity]}</span></td>
                          <td>{String(run.name || run.scrape_type || run.workflow || 'Collecte').replaceAll('_', ' ')}</td>
                          <td>{formatTimestamp(run.started_at)}</td>
                          <td>{formatDuration(run.duration_seconds)}</td>
                          <td>{items === null || items === undefined ? '—' : formatNumber(items)}</td>
                          <td>{inserted === null || inserted === undefined ? '—' : formatNumber(inserted)}</td>
                          <td>{updated === null || updated === undefined ? '—' : formatNumber(updated)}</td>
                          <td>{formatNumber(run.failed_items)}</td>
                          <td><span className={`pipeline-status status-${String(run.status || '').toLowerCase()}`}>{statusLabel(run.status)}</span></td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
