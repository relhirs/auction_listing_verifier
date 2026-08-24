import { useState } from 'react'
import { Info, X } from 'lucide-react'

export default function TooltipWrapper({ label = 'Methodology', children }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="inline-block">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-zinc-500 hover:text-amber-700 border border-zinc-300 rounded-md px-2 py-0.5 bg-white"
      >
        <Info size={12} />
        {label}
      </button>
      {open && (
        <div className="mt-2 border border-zinc-200 rounded-md bg-white p-4 text-sm text-zinc-700 leading-relaxed max-w-2xl relative">
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="absolute top-2 right-2 text-zinc-400 hover:text-zinc-700"
            aria-label="Close"
          >
            <X size={14} />
          </button>
          {children}
        </div>
      )}
    </div>
  )
}
