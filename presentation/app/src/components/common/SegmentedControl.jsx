export default function SegmentedControl({ options, value, onChange }) {
  return (
    <div className="inline-flex border border-zinc-300 rounded-md bg-white p-0.5 gap-0.5">
      {options.map((opt) => {
        const active = opt.id === value
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => onChange(opt.id)}
            className={`px-3 py-1.5 text-sm rounded-[4px] transition-colors ${
              active
                ? 'bg-amber-600 text-white font-medium'
                : 'text-zinc-600 hover:bg-zinc-100'
            }`}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
