import { useState } from 'react'
import { PIPELINE_STAGES } from '../../data/pipelineStages'
import StageDetailPanel from './StageDetailPanel'

export default function PipelineStepper() {
  const [selectedId, setSelectedId] = useState(PIPELINE_STAGES[0].id)
  const selected = PIPELINE_STAGES.find((s) => s.id === selectedId)

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-stretch divide-y sm:divide-y-0 sm:divide-x divide-zinc-200 border border-zinc-200 rounded-md bg-white overflow-hidden">
        {PIPELINE_STAGES.map((stage) => {
          const active = stage.id === selectedId
          return (
            <button
              key={stage.id}
              type="button"
              onClick={() => setSelectedId(stage.id)}
              className={`flex-1 text-left px-4 py-3 transition-colors ${
                active ? 'bg-amber-50' : 'hover:bg-zinc-50'
              }`}
            >
              <div className="text-[11px] font-mono text-zinc-400">
                {String(stage.order).padStart(2, '0')}
              </div>
              <div
                className={`text-sm font-medium ${active ? 'text-amber-800' : 'text-zinc-800'}`}
              >
                {stage.name}
              </div>
            </button>
          )
        })}
      </div>
      <div className="mt-4">
        <StageDetailPanel stage={selected} />
      </div>
    </div>
  )
}
