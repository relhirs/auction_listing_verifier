import StatTile from '../common/StatTile'
import { HEADLINE, BOOTSTRAP_CI } from '../../data/metricsData'

export default function Header() {
  return (
    <header className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 pb-12">
      <h1 className="text-3xl sm:text-5xl font-semibold text-zinc-900 max-w-3xl leading-tight">
        Catching 9 in 10 auction mistakes before anyone bids
      </h1>
      <p className="text-zinc-600 mt-4 max-w-2xl text-lg">
        I planted fake errors across 500 real Cars and Bids listings and ran the system blind to
        see what it caught, what it missed, and why.
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-10">
        <StatTile
          label="Overall accuracy"
          value={`${(HEADLINE.overallAccuracy * 100).toFixed(2)}%`}
          sublabel={`${HEADLINE.tp} of ${HEADLINE.n} caught`}
        />
        <StatTile
          label="Vs naive baseline"
          value={`+${HEADLINE.improvementPoints}pt`}
          sublabel={`baseline was ${(HEADLINE.naiveBaseline * 100).toFixed(2)}%`}
        />
        <StatTile
          label="95% confidence interval"
          value={`[${(BOOTSTRAP_CI.ciLow * 100).toFixed(2)}, ${(BOOTSTRAP_CI.ciHigh * 100).toFixed(2)}]`}
          sublabel="5,000 bootstrap resamples"
          centered
          className="col-span-2 lg:col-span-1"
          valueClassName="text-xl sm:text-2xl"
        />
        <StatTile
          label="Cost per real catch"
          value={`$${HEADLINE.costPerSuccessfulCatchUsd.toFixed(2)}`}
        />
      </div>
    </header>
  )
}
