import { useMemo, useState } from 'react'
import { ArrowUpDown } from 'lucide-react'
import Card from '../common/Card'
import Badge from '../common/Badge'
import { ECONOMICS_OVERALL, ECONOMICS_BY_ERROR_TYPE, RANKED_MOST_TO_LEAST_COST_EFFICIENT } from '../../data/economicsData'

const CHEAPEST = RANKED_MOST_TO_LEAST_COST_EFFICIENT[0]
const PRICIEST = RANKED_MOST_TO_LEAST_COST_EFFICIENT[RANKED_MOST_TO_LEAST_COST_EFFICIENT.length - 1]

const COLUMNS = [
  { key: 'label', label: 'Check' },
  { key: 'recall', label: 'Recall' },
  { key: 'precision', label: 'Precision' },
  { key: 'costPerSuccessfulCatchUsd', label: 'Cost / catch' },
  { key: 'pctOfTypeCostWastedOnMisses', label: '% wasted' },
]

export default function EconomicsTable() {
  const [sortKey, setSortKey] = useState('costPerSuccessfulCatchUsd')
  const [sortDir, setSortDir] = useState('asc')

  const rows = useMemo(() => {
    const sorted = [...ECONOMICS_BY_ERROR_TYPE]
    sorted.sort((a, b) => {
      const diff = a[sortKey] > b[sortKey] ? 1 : a[sortKey] < b[sortKey] ? -1 : 0
      return sortDir === 'asc' ? diff : -diff
    })
    return sorted
  }, [sortKey, sortDir])

  const handleSort = (key) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return (
    <Card eyebrow={`$${ECONOMICS_OVERALL.totalCostUsd.toFixed(2)} total spend across ${ECONOMICS_OVERALL.n} listings`} title="What it actually costs to catch each kind of error">
      <div className="overflow-x-auto">
        <table className="text-sm w-full min-w-[560px]">
          <thead>
            <tr className="border-b border-zinc-200">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="text-left py-2 pr-3 text-[11px] font-mono uppercase tracking-wider text-zinc-500 cursor-pointer select-none"
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    <ArrowUpDown size={11} />
                  </span>
                </th>
              ))}
              <th className="text-left py-2 text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.errorType} className="border-b border-zinc-100 hover:bg-zinc-50">
                <td className="py-2 pr-3">{r.label}</td>
                <td className="py-2 pr-3 font-mono">{(r.recall * 100).toFixed(2)}%</td>
                <td className="py-2 pr-3 font-mono">{(r.precision * 100).toFixed(2)}%</td>
                <td className="py-2 pr-3 font-mono">${r.costPerSuccessfulCatchUsd.toFixed(2)}</td>
                <td className="py-2 pr-3 font-mono">{(r.pctOfTypeCostWastedOnMisses * 100).toFixed(2)}%</td>
                <td className="py-2">
                  {r.errorType === CHEAPEST && <Badge variant="well_calibrated">cheapest</Badge>}
                  {r.errorType === PRICIEST && <Badge variant="overconfident">most expensive</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 border-t border-zinc-200 pt-3 text-sm text-zinc-600 space-y-1">
        <p>
          Transmission is the cheapest catch at about 7 cents. Drivetrain is the most expensive at
          about 24 cents, since it leans hard on photo analysis.
        </p>
        <p>
          Since the drivetrain fix, none of that spend is wasted on misses anymore. Every dollar
          it costs now actually buys a real catch.
        </p>
      </div>
    </Card>
  )
}
