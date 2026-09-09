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
        see what it caught, what it missed, and why. Two different questions: did it catch the
        planted mistake, and did it reach the right final call?
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-10">
        <StatTile
          label="Error recall"
          value={`${Math.round((HEADLINE.tp / HEADLINE.n) * 100)}%`}
          sublabel={`${HEADLINE.tp} of ${HEADLINE.n} planted mistakes caught`}
        />
        <StatTile
          label="Decision accuracy"
          value={`${Math.floor(HEADLINE.overallAccuracy * 100)}%`}
          sublabel="final verdict vs. ground truth"
        />
        <StatTile
          label="Vs naive baseline"
          value={`+${HEADLINE.improvementPoints}pt`}
          sublabel={`baseline was ${(HEADLINE.naiveBaseline * 100).toFixed(2)}%`}
        />
        <StatTile
          label="Cost per real catch"
          value={`$${HEADLINE.costPerSuccessfulCatchUsd.toFixed(2)}`}
        />
      </div>

      <div className="mt-3">
        <StatTile
          label="95% confidence interval (decision accuracy)"
          value={`[${(BOOTSTRAP_CI.ciLow * 100).toFixed(2)}, ${(BOOTSTRAP_CI.ciHigh * 100).toFixed(2)}]`}
          sublabel="5,000 bootstrap resamples"
          centered
          valueClassName="text-xl sm:text-2xl"
        />
      </div>
    </header>
  )
}
