import { formatValue } from './format'
import { EU_DAILY_LIMIT } from './pm10'

const WIDTH = 160
const HEIGHT = 32
const PAD = 2

interface SparklineProps {
  /** Parovi [vrijeme, vrijednost], poredani po vremenu */
  points: [string, number][]
  unit: string
}

/**
 * Mali graf PM10 za zadnjih 48 sati. Vodoravni položaj prati vrijeme, pa sati bez mjerenja ne
 * skraćuju razmak; isprekidana crta je dnevna granična vrijednost EU, ako je u rasponu grafa.
 */
export function Sparkline({ points, unit }: SparklineProps) {
  if (points.length < 2) return null
  const times = points.map(([time]) => Date.parse(time))
  const values = points.map(([, value]) => value)
  const [start, end] = [Math.min(...times), Math.max(...times)]
  const [low, high] = [Math.min(...values), Math.max(...values)]

  const x = (time: number) => PAD + ((time - start) / (end - start || 1)) * (WIDTH - 2 * PAD)
  const y = (value: number) =>
    high === low ? HEIGHT / 2 : PAD + (1 - (value - low) / (high - low)) * (HEIGHT - 2 * PAD)
  const line = points
    .map(
      (_, index) => `${x(times[index] ?? start).toFixed(1)},${y(values[index] ?? low).toFixed(1)}`,
    )
    .join(' ')
  const limitInRange = low < EU_DAILY_LIMIT && EU_DAILY_LIMIT < high

  return (
    <figure className="zr-sparkline">
      <svg viewBox={`0 0 ${String(WIDTH)} ${String(HEIGHT)}`} aria-hidden="true">
        {limitInRange && (
          <line x1={PAD} x2={WIDTH - PAD} y1={y(EU_DAILY_LIMIT)} y2={y(EU_DAILY_LIMIT)} />
        )}
        <polyline points={line} />
      </svg>
      <figcaption>
        48 h: od {formatValue(low, unit)} do {formatValue(high, unit)}
        {limitInRange && ' (crtkano: granica EU)'}
      </figcaption>
    </figure>
  )
}
