import { Overview, usePhysicalCatalog } from '../components/PhysicalDataViews'

export default function OverviewPage({ onNavigate }) {
  const catalog = usePhysicalCatalog()
  if (catalog.loading) return <div className="physical-page physical-loading">Loading PhysicalData...</div>
  return <Overview catalog={catalog} onNavigate={onNavigate} />
}