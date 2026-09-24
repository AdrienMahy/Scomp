import { Scraping, usePhysicalCatalog } from '../components/PhysicalDataViews'

export default function ScrapingPage() {
  const catalog = usePhysicalCatalog()
  return <Scraping catalog={catalog} onImported={catalog.reload} />
}