import { Children } from 'react'
import Reveal from '../common/Reveal'

export default function SectionWrapper({ id, eyebrow, title, subtitle, children }) {
  return (
    <section id={id} className="scroll-mt-16 py-16 border-b border-zinc-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <Reveal>
          <div className="mb-8">
            <div className="text-[11px] font-mono uppercase tracking-wider text-amber-700 mb-2">
              {eyebrow}
            </div>
            <h2 className="text-2xl sm:text-3xl font-semibold text-zinc-900">{title}</h2>
            {subtitle && <p className="text-zinc-600 mt-2 max-w-2xl">{subtitle}</p>}
          </div>
        </Reveal>
        <div className="grid grid-cols-1 gap-6">
          {Children.map(children, (child, i) => (
            <Reveal key={i} delay={i * 80}>
              {child}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
