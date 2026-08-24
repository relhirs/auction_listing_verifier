import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import Card from '../common/Card'
import TakeawayBadge from '../common/TakeawayBadge'
import TooltipWrapper from '../common/TooltipWrapper'
import { BRIER_BY_FIELD, SMOOTHING_CHANGES, OVERALL_BRIER, CONFIDENCE_FLOOR_INCIDENT, DRIVETRAIN_CONFIDENCE_FIX } from '../../data/calibrationData'
import { CHART_VERIFIED, CHART_PRIMARY, CHART_ERROR, CHART_BENCHMARK } from '../../constants/colors'

const STATUS_COLOR = {
  well_calibrated: CHART_VERIFIED,
  ok: CHART_PRIMARY,
  overconfident: CHART_ERROR,
  thin_sample: CHART_BENCHMARK,
}

export default function BrierCalibrationChart() {
  const data = BRIER_BY_FIELD.map((f) => ({ ...f, brierPct: f.brier }))

  return (
    <Card eyebrow={`Overall Brier score: ${OVERALL_BRIER.score} (n=${OVERALL_BRIER.n})`} title="Does confidence mean what it says?">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
          <CartesianGrid stroke="#E4E4E7" strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" interval={0} height={60} />
          <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} />
          <Tooltip
            contentStyle={{ border: '1px solid #E4E4E7', borderRadius: 6, fontSize: 12 }}
            formatter={(v, _n, item) => [v, `Brier (n=${item.payload.n})`]}
          />
          <Bar dataKey="brier" radius={[3, 3, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={STATUS_COLOR[d.status] || CHART_PRIMARY} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4">
        <TooltipWrapper label="What does 'smoothing' mean, and what changed?">
          <div className="space-y-4">
            <p className="text-sm text-zinc-700">
              Most checks used to report one fixed confidence number every time they fired,{' '}
              <span className="font-mono text-xs">0.9</span> no matter how far off the listing
              actually was. "Smoothing" means changing a check so its confidence scales with the
              size of the discrepancy instead: a mileage claim off by 50,000 real miles now
              reports higher confidence than one off by 6,000, rather than both reporting the
              same flat number. It was tried on 5 fields below. Lower Brier score is better; it
              measures how well a confidence number actually tracks how often the check turns out
              to be right.
            </p>

            <div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mb-2">
                Brier score, before smoothing vs. after
              </div>
              <div className="space-y-2">
                {SMOOTHING_CHANGES.map((c) => (
                  <div key={c.field} className="text-sm">
                    <span className="font-medium text-zinc-800">{c.label}</span>{' '}
                    <span className="font-mono text-xs text-zinc-500">
                      {c.before} &rarr; {c.after}
                    </span>{' '}
                    <span
                      className={`text-xs font-mono uppercase ${
                        c.verdict === 'reverted' || c.verdict === 'worse'
                          ? 'text-orange-700'
                          : 'text-emerald-700'
                      }`}
                    >
                      {c.verdict}
                    </span>
                    {c.note && <p className="text-xs text-zinc-500 mt-0.5">{c.note}</p>}
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-zinc-200">
              <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mb-1">
                A bug this work introduced, caught before shipping
              </div>
              <p className="text-xs text-zinc-500">{CONFIDENCE_FLOOR_INCIDENT.description}</p>
            </div>

            <div className="pt-3 border-t border-zinc-200">
              <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mb-1">
                Drivetrain: a related but different fix, not smoothing
              </div>
              <p className="text-xs text-zinc-500 mb-1.5">
                Drivetrain has no numeric gap to scale a formula on the way mileage or engine
                size do, so it didn't get the same treatment. Instead it uses a simpler rule: one
                specific mismatch type reports a lower fixed number, every other type still
                reports the original one.
              </p>
              <span className="font-medium text-zinc-800 text-sm">Drivetrain</span>{' '}
              <span className="font-mono text-xs text-zinc-500">
                Brier {DRIVETRAIN_CONFIDENCE_FIX.before.brier} &rarr;{' '}
                {DRIVETRAIN_CONFIDENCE_FIX.after.brier}
              </span>{' '}
              <span className="text-xs font-mono uppercase text-emerald-700">fixed</span>
              <p className="text-xs text-zinc-500 mt-1">{DRIVETRAIN_CONFIDENCE_FIX.description}</p>
              <p className="text-xs text-zinc-500 mt-1">{DRIVETRAIN_CONFIDENCE_FIX.tradeoff}</p>
            </div>
          </div>
        </TooltipWrapper>
      </div>

      <TakeawayBadge
        measures="Brier score per check field. Lower means the confidence number actually tracks how often the check is right."
        pattern="Make, duplicate photo, mileage, and missing angle are well calibrated. Color is still clearly overconfident. Drivetrain used to be, until it got fixed."
        soWhat="Color still catches real errors fine while being too sure of itself on false alarms. Drivetrain had the same problem, traced to one specific confusion (AWD vs 4WD), and fixed without losing any recall."
      />
    </Card>
  )
}
