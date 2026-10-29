import { Activity, usePhysicalCatalog } from '../components/PhysicalDataViews'

export default function ActivityPage({ onNavigate }) {
  const catalog = usePhysicalCatalog()
  return <Activity catalog={catalog} onNavigate={onNavigate} />
}