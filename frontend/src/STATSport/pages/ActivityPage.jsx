import { Activity, usePhysicalCatalog } from '../components/PhysicalDataViews'

export default function ActivityPage() {
  const catalog = usePhysicalCatalog()
  return <Activity catalog={catalog} />
}