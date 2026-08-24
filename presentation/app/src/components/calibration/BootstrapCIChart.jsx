import Card from '../common/Card'
import TakeawayBadge from '../common/TakeawayBadge'
import { BOOTSTRAP_CI } from '../../data/metricsData'
import { CHART_PRIMARY } from '../../constants/colors'

export default function BootstrapCIChart() {
  const { pointEstimate, ciLow, ciHigh } = BOOTSTRAP_CI
  const lowPct = ciLow * 100
  const highPct = ciHigh * 100
  const pointPct = pointEstimate * 100

  // Zoom the visual scale into a padded window around the CI, instead of
  // plotting these close together points on a full 0 to 100 scale where
  // they would all crowd into one small sliver and overlap.
  const domainMin = Math.floor(lowPct) - 2
  const domainMax = Math.ceil(highPct) + 2
  const toPosition = (v) => ((v - domainMin) / (domainMax - domainMin)) * 100

  const lowPos = toPosition(lowPct)
  const highPos = toPosition(highPct)
  const pointPos = toPosition(pointPct)

  return (
    <Card eyebrow="5,000 bootstrap resamples" title="How much would this number move on a different sample?">
      <div className="relative h-20 mb-2 px-2">
        <div className="absolute inset-x-2 top-8 h-1 bg-zinc-200 rounded-full" />
        <div
          className="absolute top-7 h-3 rounded-full"
          style={{
            left: `${lowPos}%`,
            width: `${highPos - lowPos}%`,
            backgroundColor: CHART_PRIMARY,
            opacity: 0.25,
          }}
        />
        <div
          className="absolute top-5 w-1 h-7 rounded-full"
          style={{ left: `${pointPos}%`, backgroundColor: CHART_PRIMARY }}
        />
        <div
          className="absolute top-16 text-xs font-mono text-zinc-500 whitespace-nowrap"
          style={{ left: `${lowPos}%`, transform: 'translateX(-50%)' }}
        >
          {lowPct.toFixed(2)}%
        </div>
        <div
          className="absolute top-0 text-xs font-mono text-zinc-900 font-semibold whitespace-nowrap"
          style={{ left: `${pointPos}%`, transform: 'translateX(-50%)' }}
        >
          {pointPct.toFixed(2)}%
        </div>
        <div
          className="absolute top-16 text-xs font-mono text-zinc-500 whitespace-nowrap"
          style={{ left: `${highPos}%`, transform: 'translateX(-50%)' }}
        >
          {highPct.toFixed(2)}%
        </div>
      </div>
      <TakeawayBadge
        pattern="The real range is about 84.51% to 90.34%. Almost six points wide, not a single fixed number."
        soWhat="87.53% is the headline number, but the honest answer isn't one number. It's a range."
      />
    </Card>
  )
}
