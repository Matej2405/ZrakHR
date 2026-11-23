import { liveKey, type LiveStation } from '../../api/live'
import { SOURCE_LABELS } from './constants'
import { formatCoordinates, formatShortTime, formatValue } from './format'
import type { StationLocation } from './locations'
import { pm10Band } from './pm10'
import { Sparkline } from './Sparkline'

// Redoslijed i nazivi metrika u oblačiću; najprije zagađenje, zatim vrijeme
const METRIC_LABELS: [string, string][] = [
  ['pm10', 'PM10'],
  ['pm2_5', 'PM2,5'],
  ['nitrogen_dioxide', 'NO₂'],
  ['ozone', 'O₃'],
  ['temperature_2m', 'Temperatura'],
  ['relative_humidity_2m', 'Vlažnost'],
  ['wind_speed_10m', 'Vjetar'],
  ['wind_direction_10m', 'Smjer vjetra'],
  ['pressure_msl', 'Tlak'],
  ['surface_pressure', 'Tlak na visini postaje'],
  ['pressure_tendency', 'Promjena tlaka (3 h)'],
]

const NO_LIVE: ReadonlyMap<string, LiveStation> = new Map()

function LiveValues({ live }: { live: LiveStation }) {
  const values = METRIC_LABELS.flatMap(([metric, label]) => {
    const item = live.values[metric]
    return item ? [{ metric, label, ...item }] : []
  })
  if (values.length === 0) return null
  const latest =
    values
      .map((item) => item.observed_at)
      .sort()
      .at(-1) ?? ''
  const pm10 = live.values.pm10

  return (
    <div className="zr-popup-live">
      <p>Mjereno {formatShortTime(latest)}</p>
      <dl>
        {values.map(({ metric, label, value, unit, observed_at }) => (
          <div key={metric}>
            <dt>{label}</dt>
            <dd>
              {formatValue(value, unit)}
              {metric === 'pm10' && pm10Band(value).aboveEuLimit && ' (iznad granice EU)'}
              {/* Neke se veličine ne mjere svaki sat (npr. promjena tlaka), pa ih označava vrijeme */}
              {observed_at !== latest && ` (${formatShortTime(observed_at)})`}
            </dd>
          </div>
        ))}
      </dl>
      {pm10 && <Sparkline points={live.trend} unit={pm10.unit} />}
    </div>
  )
}

interface StationPopupProps {
  location: StationLocation
  /** Zadnja mjerenja po ključu postaje (liveKey); postaje bez mjerenja ga nemaju */
  live?: ReadonlyMap<string, LiveStation>
}

/** Sadržaj oblačića: svaka postaja na lokaciji s izvorom, mrežom ili vrstom i zadnjim mjerenjima. */
export function StationPopup({ location, live = NO_LIVE }: StationPopupProps) {
  return (
    <div className="zr-popup">
      {location.stations.map((station) => {
        const measured = live.get(liveKey(station.source, station.external_id))
        return (
          <div key={station.external_id} className="zr-popup-station">
            <strong className="zr-popup-name">{station.name}</strong>
            <dl>
              <dt>Izvor</dt>
              <dd>
                {SOURCE_LABELS[station.source].name}, {SOURCE_LABELS[station.source].measures}
              </dd>
              {station.source === 'azo' ? (
                <>
                  <dt>Mreža</dt>
                  <dd>{station.network}</dd>
                </>
              ) : (
                <>
                  <dt>Vrsta</dt>
                  <dd>{station.automatic ? 'automatska postaja' : 'postaja s motriteljem'}</dd>
                </>
              )}
            </dl>
            {measured && <LiveValues live={measured} />}
          </div>
        )
      })}
      <p className="zr-popup-coordinates">{formatCoordinates(location.lat, location.lon)}</p>
    </div>
  )
}
