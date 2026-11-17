import { Page, Planned } from '../components/Page'

export function AnalysisPage() {
  return (
    <Page
      title="Analiza"
      lede="Kako temperatura, vjetar, tlak i vlažnost utječu na PM10 i PM2.5 te koliko je točna prognoza zagađenja u odnosu na izmjerene vrijednosti."
    >
      <Planned>
        Analiza utjecaja vremena i usporedba prognoza (CAMS i vlastiti model) s mjerenjima stižu u
        iteraciji KT IV.
      </Planned>
    </Page>
  )
}
