import { THRESHOLD_SWEEP, CONFIDENCE_FLOOR } from '../../constants/thresholds'

export default function ThresholdSlider({ index, onChange }) {
  const value = THRESHOLD_SWEEP[index]

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
        <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          Confidence floor cutoff
        </span>
        <span className="font-mono text-lg text-amber-700 leading-none">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={THRESHOLD_SWEEP.length - 1}
        step={1}
        value={index}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-amber-600"
      />
      <div className="flex mt-2 px-0.5">
        {THRESHOLD_SWEEP.map((t, i) => (
          <span
            key={t}
            className={`flex-1 text-center text-[10px] font-mono whitespace-nowrap ${
              i === index ? 'text-amber-700 font-semibold' : 'text-zinc-400'
            }`}
          >
            {t.toFixed(2)}
          </span>
        ))}
      </div>
      {value === CONFIDENCE_FLOOR && (
        <div className="text-xs text-amber-700 font-mono mt-2">this is the real production floor</div>
      )}
    </div>
  )
}
