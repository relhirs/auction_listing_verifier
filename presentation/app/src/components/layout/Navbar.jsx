import { useEffect, useState } from 'react'

const SECTIONS = [
  { id: 'system', label: 'System' },
  { id: 'what-changed', label: 'What changed' },
  { id: 'not-luck', label: 'Not luck' },
  { id: 'trust', label: 'Trust' },
  { id: 'stress-test', label: 'Stress test' },
  { id: 'bottom-line', label: 'Bottom line' },
]

export default function Navbar() {
  const [active, setActive] = useState('system')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActive(entry.target.id)
        })
      },
      { rootMargin: '-40% 0px -50% 0px' }
    )
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  return (
    <nav className="sticky top-0 z-10 bg-[#F9F9F8]/90 backdrop-blur border-b border-zinc-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center gap-1 overflow-x-auto">
        {SECTIONS.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className={`whitespace-nowrap text-sm px-3 py-3 border-b-2 transition-colors ${
              active === s.id
                ? 'border-amber-600 text-amber-700 font-medium'
                : 'border-transparent text-zinc-500 hover:text-zinc-800'
            }`}
          >
            {s.label}
          </a>
        ))}
      </div>
    </nav>
  )
}
