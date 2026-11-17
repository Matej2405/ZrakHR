import { Page, Planned } from '../components/Page'

export function DashboardPage() {
  return (
    <Page
      title="Pregled"
      lede="Koncentracije lebdećih čestica PM10 i PM2.5 i vremenski uvjeti za Zagreb, Rijeku, Split, Osijek i Slavonski Brod."
    >
      <Planned>
        Ovdje će biti grafovi vremenskih nizova s filtrima po gradu, onečišćujućoj tvari i
        razdoblju. Stižu u iteraciji KT III, kada backend počne posluživati mjerenja preko REST
        API-ja.
      </Planned>
    </Page>
  )
}
