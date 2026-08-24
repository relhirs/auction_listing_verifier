import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import Card from '../common/Card'
import ThresholdSlider from './ThresholdSlider'
import { THRESHOLD_SWEEP, BY_THRESHOLD } from '../../data/stressTestData'
import { ERROR_TYPE_LABELS } from '../../constants/filters'
import { CHART_PRIMARY, CHART_VERIFIED } from '../../constants/colors'

export default function ThresholdCurveChart() {
  const [index, setIndex] = useState(THRESHOLD_SWEEP.indexOf(0.7))
  const threshold = THRESHOLD_SWEEP[index]
  const row = BY_THRESHOLD[String(threshold)]

  const data = Object.entries(row).map(([errorType, m]) => ({
    label: ERROR_TYPE_LABELS[errorType] || errorType,
    precision: m.precision == null ? 0 : m.precision * 100,
    recall: m.recall * 100,
  }))

  return (
    <Card title="What happens if the confidence floor moved?">
      <ThresholdSlider index={index} onChange={setIndex} />

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
          <CartesianGrid stroke="#E4E4E7" strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" interval={0} height={60} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ border: '1px solid #E4E4E7', borderRadius: 6, fontSize: 12 }}
            formatter={(v, name) => [`${v.toFixed(2)}%`, name]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="precision" name="Precision" fill={CHART_PRIMARY} radius={[3, 3, 0, 0]} />
          <Bar dataKey="recall" name="Recall" fill={CHART_VERIFIED} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 border-t border-zinc-200 pt-3 text-sm text-zinc-600 space-y-1">
        <p>
          Push the floor below 0.70 and precision craters as noisy low confidence flags flood in.
          Push it above 0.85 and several checks lose almost all their recall at once.
        </p>
        <p>0.70 sits in the narrow window where both numbers still hold up. That is why it is the real floor.</p>
      </div>
    </Card>
  )
}
