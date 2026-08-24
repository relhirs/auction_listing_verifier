export default function StatTile({ label, value, sublabel, delta, centered = false, className = '', valueClassName = 'text-2xl sm:text-3xl' }) {
  return (
    <div className={`bg-white border border-zinc-200 rounded-md p-4 ${centered ? 'text-center' : ''} ${className}`}>
      <div className={`font-mono ${valueClassName} text-zinc-900 whitespace-nowrap`}>{value}</div>
      <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mt-1">
        {label}
      </div>
      {sublabel && <div className="text-xs text-zinc-500 mt-1">{sublabel}</div>}
      {delta && (
        <div className="text-xs font-mono text-amber-700 mt-1">{delta}</div>
      )}
    </div>
  )
}
