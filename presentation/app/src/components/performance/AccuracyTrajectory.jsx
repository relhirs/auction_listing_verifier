import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import Card from '../common/Card'
import { HEADLINE } from '../../data/metricsData'
import { CHART_PRIMARY, CHART_BENCHMARK, CHART_ERROR } from '../../constants/colors'

export default function AccuracyTrajectory() {
  const data = HEADLINE.accuracyTrajectory.map((v, i) => ({
    label: HEADLINE.trajectoryLabels[i],
    accuracy: v * 100,
    flagEverything: HEADLINE.flagEverythingBaseline * 100,
    naiveBaseline: HEADLINE.naiveBaseline * 100,
  }))

  return (
    <Card eyebrow="Overall accuracy over time" title="Two fixes, three points">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid stroke="#E4E4E7" strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis domain={[30, 95]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ border: '1px solid #E4E4E7', borderRadius: 6, fontSize: 12 }}
            formatter={(v, name) => [`${v.toFixed(2)}%`, name]}
          />
          <Legend verticalAlign="top" height={44} wrapperStyle={{ fontSize: 11 }} />
          <Line
            type="monotone"
            dataKey="flagEverything"
            name="Flag every listing, always"
            stroke={CHART_ERROR}
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={{ r: 4, fill: CHART_ERROR, strokeWidth: 0 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="naiveBaseline"
            name="Always guess the most common verdict"
            stroke={CHART_BENCHMARK}
            strokeWidth={1.5}
            strokeDasharray="2 3"
            dot={{ r: 4, fill: CHART_BENCHMARK, strokeWidth: 0 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="accuracy"
            name="This system"
            stroke={CHART_PRIMARY}
            strokeWidth={2}
            dot={{ r: 5 }}
            activeDot={{ r: 7 }}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-sm text-zinc-600 mt-3">
        Accuracy jumped from 77.5% to 87.5% after fixing two bugs across the 500 real listings.
        For comparison, simply flagging every listing gets 40.64%. Always guessing the most
        common outcome (needs review) hits 51.31% because that is the right call for about half
        the data. Both big improvements came down to one core issue. The system kept quietly
        fixing fake errors back to the real facts before running the actual check.
      </p>
    </Card>
  )
}
