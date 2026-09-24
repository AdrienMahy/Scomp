import { Players, usePhysicalCatalog } from '../components/PhysicalDataViews'

export default function PlayersPage() {
  const catalog = usePhysicalCatalog()
  return <Players catalog={catalog} />
}