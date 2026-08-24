import { useMemo, useState } from 'react'
import { Info, X, ChevronDown, ChevronUp } from 'lucide-react'
import Card from '../common/Card'
import Badge from '../common/Badge'
import TakeawayBadge from '../common/TakeawayBadge'
import { CHECKS } from '../../data/checksData'
import { BRIER_BY_FIELD } from '../../data/calibrationData'
import { CHART_PRIMARY, CHART_BENCHMARK } from '../../constants/colors'

const BRIER_BY_ROC_FIELD = Object.fromEntries(BRIER_BY_FIELD.map((f) => [f.field, f]))

const COLUMNS = [
  { key: 'label', label: 'Check', sortable: false },
  { key: 'recall', label: 'Recall', sortable: true },
  { key: 'precision', label: 'Precision', sortable: true },
  { key: 'costPerCatchUsd', label: 'Cost / catch', sortable: true },
]

const GRID = '180px 1fr 1fr 1fr'

function PercentBar({ value }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${value * 100}%`, backgroundColor: CHART_PRIMARY }}
        />
      </div>
      <span className="font-mono text-xs text-zinc-800 w-12 text-right shrink-0">
        {(value * 100).toFixed(1)}%
      </span>
    </div>
  )
}

function CostBar({ value, max }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${(value / max) * 100}%`, backgroundColor: CHART_PRIMARY }}
        />
      </div>
      <span className="font-mono text-xs text-zinc-800 w-12 text-right shrink-0">
        ${value.toFixed(2)}
      </span>
    </div>
  )
}

// Same visual language as calibration/BootstrapCIChart.jsx (shaded band + a
// tick for the point estimate), but the numbers are always printed as text
// too, so nothing depends on eyeballing pixel widths.
function RecallCell({ recall, ci, n }) {
  const [low, high] = ci
  return (
    <div>
      <PercentBar value={recall} />
      <div className="relative h-2 mt-1 mb-0.5">
        <div className="absolute inset-0 rounded-full bg-zinc-100" />
        <div
          className="absolute inset-y-0 rounded-full"
          style={{
            left: `${low * 100}%`,
            width: `${Math.max((high - low) * 100, 1.5)}%`,
            backgroundColor: CHART_BENCHMARK,
            opacity: 0.35,
          }}
        />
      </div>
      <p className="text-[11px] font-mono text-zinc-500">
        CI {(low * 100).toFixed(1)}–{(high * 100).toFixed(1)}% &middot; n={n}
      </p>
    </div>
  )
}

// Every row gets this, not just the ones with a hand-written note. Status
// color is the only color signal in the table (see Badge), so the toggle
// and panel here borrow that same color instead of an unrelated accent
// (previously zinc text that turned amber on hover, tied to nothing) so a
// reader can see at a glance which explanation goes with which status.
const STATUS_STYLES = {
  reliable: {
    text: 'text-emerald-700',
    border: 'border-emerald-300',
    hoverBg: 'hover:bg-emerald-50',
    panelBorder: 'border-emerald-200',
  },
  overconfident: {
    text: 'text-orange-700',
    border: 'border-orange-300',
    hoverBg: 'hover:bg-orange-50',
    panelBorder: 'border-orange-200',
  },
}
const DEFAULT_STATUS_STYLE = {
  text: 'text-zinc-600',
  border: 'border-zinc-300',
  hoverBg: 'hover:bg-zinc-50',
  panelBorder: 'border-zinc-200',
}

function explainStatus(c, n) {
  if (c.note) return c.note
  const [low, high] = c.bootstrapRecallCi
  const ciWidth = (high - low) * 100
  const ciNote =
    ciWidth >= 5
      ? `The confidence interval is wider than most checks here because it's based on fewer real cases (n=${n}).`
      : `With n=${n} real cases, the interval stays tight.`
  return `Catches ${(c.recall * 100).toFixed(1)}% of real cases at ${(c.precision * 100).toFixed(1)}% precision. ${ciNote} That combination is why this check is marked "${c.status.replace(/_/g, ' ')}".`
}

function StatusDisclosure({ check, n, brier }) {
  const [open, setOpen] = useState(false)
  const style = STATUS_STYLES[check.status] || DEFAULT_STATUS_STYLE
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider bg-white rounded-md px-2 py-0.5 border ${style.text} ${style.border} ${style.hoverBg}`}
      >
        <Info size={12} />
        Why this status
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <div className={`mt-2 border rounded-md bg-white p-3 text-xs text-zinc-700 leading-relaxed relative ${style.panelBorder}`}>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="absolute top-2 right-2 text-zinc-400 hover:text-zinc-700"
            aria-label="Close"
          >
            <X size={12} />
          </button>
          <p className="pr-4">{explainStatus(check, n)}</p>
          {brier && (
            <p className="mt-2 pt-2 border-t border-zinc-200 font-mono text-zinc-500">
              Brier score across all real firings: {brier.brier} (n={brier.n}). Lower is better
              calibrated; 0 is perfect. This is a different, larger count than the recall n above,
              which is just the synthetic eval cases for this check.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function PerCheckBreakdown() {
  const [sortKey, setSortKey] = useState('recall')
  const [sortDir, setSortDir] = useState('desc')

  const maxCost = useMemo(() => Math.max(...CHECKS.map((c) => c.costPerCatchUsd)), [])

  const sorted = useMemo(() => {
    const rows = [...CHECKS]
    rows.sort((a, b) => (a[sortKey] - b[sortKey]) * (sortDir === 'desc' ? -1 : 1))
    return rows
  }, [sortKey, sortDir])

  const handleSort = (key) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  return (
    <Card title="Which checks are solid, which are thin">
      <div
        className="grid gap-4 pb-2 mb-1 border-b border-zinc-200"
        style={{ gridTemplateColumns: GRID }}
      >
        {COLUMNS.map((col) =>
          col.sortable ? (
            <button
              key={col.key}
              onClick={() => handleSort(col.key)}
              className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-zinc-500 hover:text-zinc-800 text-left"
            >
              {col.label}
              {sortKey === col.key &&
                (sortDir === 'desc' ? <ChevronDown size={12} /> : <ChevronUp size={12} />)}
            </button>
          ) : (
            <div key={col.key} className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
              {col.label}
            </div>
          )
        )}
      </div>

      <div className="divide-y divide-zinc-100">
        {sorted.map((c) => {
          const n = c.tp + c.fn + c.fp
          const brier = c.status === 'overconfident' ? BRIER_BY_ROC_FIELD[c.rocField] : null
          return (
            <div
              key={c.id}
              className="grid gap-4 py-3 items-start"
              style={{ gridTemplateColumns: GRID }}
            >
              <div>
                <div className="text-sm font-medium text-zinc-900">{c.label}</div>
                <Badge variant={c.status} className="mt-1">
                  {c.status.replace(/_/g, ' ')}
                </Badge>
                <StatusDisclosure check={c} n={n} brier={brier} />
              </div>
              <RecallCell recall={c.recall} ci={c.bootstrapRecallCi} n={n} />
              <PercentBar value={c.precision} />
              <CostBar value={c.costPerCatchUsd} max={maxCost} />
            </div>
          )
        })}
      </div>

      <TakeawayBadge
        measures="Recall, precision, and cost per catch for every check, all shown at once. Recall carries a 95% bootstrap confidence interval and the real sample size (n) it was measured on."
        pattern="Most checks sit at or near 100% recall with a tight interval. Year is the widest gap, 83.33% with a CI of 77.33-88.67%, because it still has 25 real misses out of a much larger n. Color is the one check flagged overconfident, despite catching 96.3% of real mismatches."
        soWhat="Bar length is magnitude, the badge is status. Color's bars look as strong as any other check's. Its problem is calibration on false alarms, not recall, click 'why this status' on that row for the real Brier number behind the label."
      />
    </Card>
  )
}
