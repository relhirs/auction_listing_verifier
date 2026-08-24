export default function TakeawayBadge({ measures, pattern, soWhat }) {
  const items = [measures, pattern, soWhat].filter(Boolean)
  return (
    <div className="border border-zinc-200 rounded-md bg-zinc-50 p-4 text-sm leading-relaxed">
      <ul className="space-y-2">
        {items.map((text, i) => {
          const isLast = i === items.length - 1
          return (
            <li key={i} className="flex gap-2.5">
              <span
                className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${
                  isLast ? 'bg-amber-500' : 'bg-zinc-300'
                }`}
              />
              <span className="text-zinc-800">{text}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
