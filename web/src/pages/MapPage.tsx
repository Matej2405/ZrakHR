import { Page, Planned } from '../components/Page'

export function MapPage() {
  return (
    <Page
      title="Karta postaja"
      lede="Mjerne postaje DHMZ-a (vrijeme) i AZO-a (kvaliteta zraka) na karti Hrvatske."
    >
      <Planned>
        Karta s postajama iz statičkog izvoza stiže u sljedećem koraku, prije REST API-ja.
      </Planned>
    </Page>
  )
}
