export default function Footer() {
  return (
    <footer className="py-10">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 text-sm text-zinc-500 leading-relaxed">
        <p>
          Every number on this page comes straight from the eval pipeline's real output files,
          <span className="font-mono text-xs mx-1">eval/results.json</span>
          and
          <span className="font-mono text-xs mx-1">analysis/output/*.json</span>
          in the project repo. Nothing here is estimated or rounded by hand.
        </p>
      </div>
    </footer>
  )
}
