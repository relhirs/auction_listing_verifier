import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import Card from '../common/Card'
import SegmentedControl from '../common/SegmentedControl'
import TooltipWrapper from '../common/TooltipWrapper'
import { WEIGHTING_SCHEMES } from '../../constants/filters'
import {
  INJECTION_REWEIGHTING,
  ERROR_TYPE_SAMPLE_SIZES,
  COMMUNITY_ERROR_CASES,
} from '../../data/stressTestData'
import { CHART_PRIMARY, CHART_VERIFIED } from '../../constants/colors'

export default function WeightingSchemeToggle() {
  const [scheme, setScheme] = useState('current_realized')
  const current = INJECTION_REWEIGHTING[scheme]

  const data = Object.entries(INJECTION_REWEIGHTING).map(([id, v]) => ({
    id,
    label: v.label,
    recall: v.meanRecall * 100,
    accuracy: v.meanVerdictAccuracy * 100,
    active: id === scheme,
  }))

  return (
    <Card title="What if the test set had a different mix of errors?">
      <div className="mb-4">
        <SegmentedControl options={WEIGHTING_SCHEMES} value={scheme} onChange={setScheme} />
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid stroke="#E4E4E7" strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis domain={[80, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ border: '1px solid #E4E4E7', borderRadius: 6, fontSize: 12 }}
            formatter={(v, name) => [`${v.toFixed(2)}%`, name]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="recall" name="Mean recall" fill={CHART_PRIMARY} radius={[3, 3, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={CHART_PRIMARY} fillOpacity={d.active ? 1 : 0.3} />
            ))}
          </Bar>
          <Bar dataKey="accuracy" name="Verdict accuracy" fill={CHART_VERIFIED} radius={[3, 3, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={CHART_VERIFIED} fillOpacity={d.active ? 1 : 0.3} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="border border-zinc-200 rounded-md p-3">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">Mean recall</div>
          <div className="font-mono text-2xl text-zinc-900">{(current.meanRecall * 100).toFixed(2)}%</div>
        </div>
        <div className="border border-zinc-200 rounded-md p-3">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">Verdict accuracy</div>
          <div className="font-mono text-2xl text-zinc-900">{(current.meanVerdictAccuracy * 100).toFixed(2)}%</div>
        </div>
      </div>

      {scheme === 'uniform' && (
        <div className="mt-4 text-xs text-zinc-500">
          <p className="text-zinc-600 mb-2">
            This eval set has very uneven sample sizes per error type: Year has 150 real cases,
            Drivetrain has only 20. A straight average gets pulled around by whichever type
            happens to have the most rows. Equal weighting instead gives all 9 injected error
            types the same 1/9 share of the average, no matter how many real rows back them, so no
            single over-represented type can carry the result.
          </p>
          <div className="font-mono uppercase tracking-wider text-[11px] text-zinc-500 mb-1.5">
            Real sample size per error type, before it gets flattened to 1/9 each
          </div>
          <table className="text-xs w-full max-w-xs">
            <tbody>
              {ERROR_TYPE_SAMPLE_SIZES.map((t) => (
                <tr key={t.label} className="border-b border-zinc-100 last:border-b-0">
                  <td className="py-1 text-zinc-600">{t.label}</td>
                  <td className="py-1 text-right font-mono text-zinc-800">{t.n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {scheme === 'real_world_informed' && (
        <div className="mt-4 text-xs text-zinc-500">
          <p className="text-zinc-600 mb-2">
            An automated scrape pulled over 100 possible discrepancies flagged by the community in
            real Cars and Bids comment threads. After manual review only 24 held up as true
            confirmed errors. Weighting the eval against this real world mix shows how the system
            would perform on the mistakes real buyers and sellers actually catch, instead of just
            the mix of errors this project planted.
          </p>
          <TooltipWrapper label="Show what these 24 cases actually were">
            <div className="space-y-3">
              <p className="text-xs text-zinc-500">
                A couple of these are an approximate category best fit, not an exact match, since
                the community's free-text reports don't cleanly split into this project's fixed 4
                categories. Noted inline where that happens.
              </p>
              <ul className="space-y-2">
                {COMMUNITY_ERROR_CASES.map((e, i) => (
                  <li key={i} className="flex gap-2 text-xs text-zinc-600 leading-relaxed">
                    <span className="mt-1 h-1 w-1 rounded-full bg-zinc-300 shrink-0" />
                    <span>{e.summary}</span>
                  </li>
                ))}
              </ul>
            </div>
          </TooltipWrapper>
        </div>
      )}

      <div className="mt-4 border-t border-zinc-200 pt-3 text-sm text-zinc-600 space-y-1">
        <p>
          The mix this project actually tested scores the lowest of the three. Equal weighting
          and the real world mix both come back higher.
        </p>
        <p>
          That is the honest way to read the 87.5% headline. It is not being flattered by an easy
          error mix. If anything, real world performance is probably a bit better than that.
        </p>
      </div>
    </Card>
  )
}
