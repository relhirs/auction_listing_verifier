import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceDot, ResponsiveContainer } from 'recharts'
import Card from '../common/Card'
import { K_VALUES, RECALL_CURVES, CURRENT_OPERATING_POINT, DUPLICATE_PHOTO_NOTE } from '../../data/stressTestData'
import { CHART_PRIMARY, CHART_VERIFIED, CHART_ERROR } from '../../constants/colors'

const SERIES = [
  { key: 'missing_angle', label: 'Missing angle', color: CHART_VERIFIED },
  { key: 'color_error', label: 'Color', color: CHART_PRIMARY },
  { key: 'duplicate_photo', label: 'Duplicate photo', color: CHART_ERROR },
]

export default function PhotoSamplingChart() {
  const data = K_VALUES.map((k) => {
    const row = { k: String(k) }
    SERIES.forEach((s) => {
      const point = RECALL_CURVES[s.key].find((p) => String(p.k) === String(k))
      row[s.key] = point ? point.meanRecall * 100 : null
    })
    return row
  })

  return (
    <Card eyebrow="What if fewer photos were sampled per listing" title="How many photos do you actually need to check?">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid stroke="#E4E4E7" strokeDasharray="3 3" />
          <XAxis dataKey="k" tick={{ fontSize: 11 }} />
          <YAxis
            domain={[0, 100]}
            unit="%"
            tick={{ fontSize: 11 }}
            label={{ value: 'Recall', angle: -90, position: 'insideLeft', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ border: '1px solid #E4E4E7', borderRadius: 6, fontSize: 12 }}
            formatter={(v, name) => [`${v.toFixed(2)}%`, name]}
          />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11 }} />
          {SERIES.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} dot={{ r: 3 }} />
          ))}
          <ReferenceDot
            x="full"
            y={CURRENT_OPERATING_POINT.recallAtFullSampling.missing_angle * 100}
            r={5}
            fill="#18181B"
            stroke="none"
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="text-center text-[11px] text-zinc-500 -mt-1 mb-2">Photos sampled</div>
      <p className="text-xs text-zinc-500 mt-2">
        Today's real average is {CURRENT_OPERATING_POINT.avgPhotosPerListing.toFixed(2)} photos per listing, costing about $
        {CURRENT_OPERATING_POINT.avgCostPerListingUsd.toFixed(2)} each.
      </p>
      <p className="text-xs text-zinc-500 mt-1">{DUPLICATE_PHOTO_NOTE}</p>
      <div className="mt-4 border-t border-zinc-200 pt-3 text-sm text-zinc-600 space-y-1">
        <p>
          Missing angle and color hold up fine even at 2 photos. Duplicate photo collapses hard,
          since it needs both copies of an image to survive the sample.
        </p>
        <p>
          If cost mattered more than it does today, missing angle and color could run on far
          fewer photos. Duplicate photo genuinely needs the full set.
        </p>
      </div>
    </Card>
  )
}
