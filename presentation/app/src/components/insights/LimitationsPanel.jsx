import Card from '../common/Card'
import Badge from '../common/Badge'
import { LIMITATIONS } from '../../data/insightsData'

export default function LimitationsPanel() {
  return (
    <Card title="Open limitations">
      <ul className="space-y-3">
        {LIMITATIONS.map((item, i) => (
          <li
            key={i}
            className="grid grid-cols-1 sm:grid-cols-[9rem_1fr] items-start gap-x-3 gap-y-1.5 text-sm text-zinc-700"
          >
            <Badge
              className="justify-self-start"
              variant={item.badge === 'n=1' || item.badge === 'unvalidated' ? 'thin_sample' : 'artifact'}
            >
              {item.badge}
            </Badge>
            <span className="leading-relaxed">{item.text}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}
