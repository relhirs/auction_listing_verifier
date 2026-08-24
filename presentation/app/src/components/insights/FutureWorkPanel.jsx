import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import Card from '../common/Card'
import { FUTURE_WORK } from '../../data/insightsData'

export default function FutureWorkPanel() {
  const [openCategory, setOpenCategory] = useState(FUTURE_WORK[0].category)

  return (
    <Card title="What I would do differently">
      <p className="text-sm text-zinc-600 mb-4">
        Things I would change or add if I built this again, now that I have gone through it once.
      </p>
      <div className="divide-y divide-zinc-200">
        {FUTURE_WORK.map((group) => {
          const open = group.category === openCategory
          return (
            <div key={group.category} className="py-3">
              <button
                type="button"
                onClick={() => setOpenCategory(open ? null : group.category)}
                className="flex items-center justify-between w-full text-left"
              >
                <span className="font-mono text-[11px] uppercase tracking-wider text-zinc-500">
                  {group.category}
                </span>
                {open ? <ChevronUp size={16} className="text-zinc-400" /> : <ChevronDown size={16} className="text-zinc-400" />}
              </button>
              {open && (
                <ul className="mt-3 space-y-3">
                  {group.items.map((item, i) => (
                    <li key={i} className="text-sm">
                      <span className="font-medium text-zinc-900">{item.title}</span>
                      <p className="text-zinc-600 leading-relaxed mt-0.5">{item.text}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}
