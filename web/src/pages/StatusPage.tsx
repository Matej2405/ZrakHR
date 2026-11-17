import { Page, Planned } from '../components/Page'

export function StatusPage() {
  return (
    <Page
      title="Status prikupljanja"
      lede="Kada su podaci zadnji put prikupljeni, koliko je zapisa spremljeno i gdje u nizovima nedostaju sati."
    >
      <Planned>Stranica stiže u iteraciji KT IV i oslanja se na /health endpoint backenda.</Planned>
    </Page>
  )
}
