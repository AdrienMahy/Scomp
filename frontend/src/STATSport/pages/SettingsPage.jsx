import { Settings, usePhysicalCatalog } from '../components/PhysicalDataViews'

export default function SettingsPage() {
  const catalog = usePhysicalCatalog()
  return <Settings catalog={catalog} />
}