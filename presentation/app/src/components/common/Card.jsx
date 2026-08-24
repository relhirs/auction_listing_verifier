export default function Card({ eyebrow, title, children, className = '' }) {
  return (
    <div className={`bg-white border border-zinc-200 rounded-md p-5 ${className}`}>
      {eyebrow && (
        <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mb-1">
          {eyebrow}
        </div>
      )}
      {title && <h3 className="text-base font-semibold text-zinc-900 mb-3">{title}</h3>}
      {children}
    </div>
  )
}
