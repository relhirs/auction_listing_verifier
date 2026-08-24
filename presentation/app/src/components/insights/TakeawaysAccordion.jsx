import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import Card from '../common/Card'
import { INSIGHTS } from '../../data/insightsData'

export default function TakeawaysAccordion() {
  const [openId, setOpenId] = useState(INSIGHTS[0].id)

  return (
    <Card title="Takeaways">
      <div className="divide-y divide-zinc-200">
        {INSIGHTS.map((item) => {
          const open = item.id === openId
          return (
            <div key={item.id} className="py-3">
              <button
                type="button"
                onClick={() => setOpenId(open ? null : item.id)}
                className="flex items-center justify-between w-full text-left"
              >
                <span className="font-medium text-zinc-900">{item.title}</span>
                {open ? <ChevronUp size={16} className="text-zinc-400" /> : <ChevronDown size={16} className="text-zinc-400" />}
              </button>
              {open && (
                <ul className="mt-2 space-y-2 text-sm text-zinc-600">
                  {item.lines.map((line, i) => (
                    <li key={i} className="flex gap-2.5">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-zinc-300 shrink-0" />
                      <span>{line}</span>
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
