import Badge from '../common/Badge'

export default function StageDetailPanel({ stage }) {
  if (!stage) return null
  return (
    <div
      className={`border rounded-md p-5 ${
        stage.highlight ? 'border-amber-400 bg-amber-50' : 'border-zinc-200 bg-white'
      }`}
    >
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <h4 className="text-lg font-semibold text-zinc-900">{stage.name}</h4>
        <Badge variant={stage.type}>{stage.type}</Badge>
        {stage.highlight && <Badge variant="reliable">key decision</Badge>}
      </div>
      <div className="text-xs font-mono text-zinc-500 mb-3">{stage.module}</div>
      <p className="text-zinc-700 text-sm mb-2">{stage.summary}</p>
      <p className="text-zinc-600 text-sm">{stage.detail}</p>
    </div>
  )
}
