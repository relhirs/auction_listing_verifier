const VARIANT_CLASSES = {
  llm: 'bg-amber-50 border-amber-300 text-amber-800',
  deterministic: 'bg-zinc-100 border-zinc-300 text-zinc-700',
  hybrid: 'bg-blue-50 border-blue-300 text-blue-800',
  reliable: 'bg-emerald-50 border-emerald-300 text-emerald-800',
  well_calibrated: 'bg-emerald-50 border-emerald-300 text-emerald-800',
  ok: 'bg-blue-50 border-blue-300 text-blue-800',
  overconfident: 'bg-orange-50 border-orange-300 text-orange-800',
  thin_sample: 'bg-zinc-100 border-zinc-300 text-zinc-600',
  few_positive_examples: 'bg-zinc-100 border-zinc-300 text-zinc-600',
  reverted: 'bg-orange-50 border-orange-300 text-orange-800',
  artifact: 'bg-zinc-100 border-zinc-300 text-zinc-600',
  default: 'bg-zinc-100 border-zinc-300 text-zinc-700',
}

export default function Badge({ variant = 'default', children, className = '' }) {
  const classes = VARIANT_CLASSES[variant] || VARIANT_CLASSES.default
  return (
    <span
      className={`inline-flex items-center gap-1 border rounded-md px-2 py-0.5 text-[11px] font-mono uppercase tracking-wider whitespace-nowrap ${classes} ${className}`}
    >
      {children}
    </span>
  )
}
