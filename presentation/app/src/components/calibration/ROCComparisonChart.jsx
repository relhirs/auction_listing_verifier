import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from 'recharts'
import Card from '../common/Card'
import Badge from '../common/Badge'
import TakeawayBadge from '../common/TakeawayBadge'
import { ROC_DATA } from '../../data/rocData'
import { CHART_PRIMARY, CHART_BENCHMARK } from '../../constants/colors'

function buildRows() {
  return Object.entries(ROC_DATA)
    .map(([field, d]) => ({
      field,
      label: d.label,
      auc: d.auc,
      nPositive: d.nPositive,
      fewPositiveExamples: d.fewPositiveExamples,
    }))
    .sort((a, b) => b.auc - a.auc)
}

export default function ROCComparisonChart() {
  const data = buildRows()

  return (
    <Card eyebrow="AUC per check, sorted high to low" title="Does confidence actually rank real errors above clean listings?">
      <p className="text-sm text-zinc-600 mb-3">
        AUC measures how well the model spots real problems. It tells you the chance that the
        model will flag an actual error as more suspicious than a clean listing. A score of 1.0
        means it always ranks the real error first. A score of 0.5 means it is basically a coin
        flip.
      </p>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
          <CartesianGrid stroke="#E4E4E7" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="label" width={130} tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ border: '1px solid #E4E4E7', borderRadius: 6, fontSize: 12 }}
            formatter={(v, _n, item) => [
              `${v.toFixed(2)} AUC (n=${item.payload.nPositive})`,
              item.payload.label,
            ]}
          />
          <ReferenceLine x={0.5} stroke={CHART_BENCHMARK} strokeDasharray="4 4" label={{ value: 'coin flip', position: 'top', fontSize: 10, fill: CHART_BENCHMARK }} />
          <Bar dataKey="auc" radius={[0, 3, 3, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.fewPositiveExamples ? CHART_BENCHMARK : CHART_PRIMARY} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap gap-2 mt-3">
        {data
          .filter((d) => d.fewPositiveExamples)
          .map((d) => (
            <div key={d.field} className="text-xs font-mono flex items-center gap-1">
              <span>{d.label}</span>
              <Badge variant="few_positive_examples">n={d.nPositive}</Badge>
            </div>
          ))}
      </div>

      <TakeawayBadge
        pattern="Nine of ten checks sit at 0.94 or higher. Engine cylinders sits at 0.50, right around chance."
        soWhat="Engine cylinders isn't a bad check, it just has only 1 real example in the whole corpus. Not enough data to call it either way."
      />
    </Card>
  )
}
