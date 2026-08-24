import Card from '../common/Card'
import TakeawayBadge from '../common/TakeawayBadge'
import TooltipWrapper from '../common/TooltipWrapper'
import { MCNEMAR } from '../../data/metricsData'

export default function McNemarPanel() {
  const { before, after, contingencyTable, pValue, correctionNote, powerNote } = MCNEMAR

  return (
    <Card title="Was the fix real, or just luck?">
      <p className="text-sm text-zinc-600 mb-4">
        The drivetrain check compares what a listing claims (all wheel drive, four wheel drive,
        and so on) against what the VIN itself decodes. For a while it only caught 65% of real
        drivetrain mismatches, missing more than a third of them. Digging into the 7 real misses
        turned up two separate bugs. Five of them were a bookkeeping problem, not a check
        problem: the code had already been updated to skip two kinds of unwinnable test cases,
        like claiming front wheel vs. all wheel drive against a VIN that only decodes to "2WD,"
        which no VIN can settle either way, but the eval's test file was never regenerated to
        drop those cases, so it kept grading the check on tests it could never pass. The other 2
        misses were a real bug, and the same one found in the make check: a listing would claim
        "4WD" as the planted lie, but the extraction step read the surrounding text, recognized
        the real drivetrain, and quietly wrote the correct value into the structured data before
        the check ever saw the lie to catch it. Fixing the stale test file and adding the same
        "don't infer the real value from context" instruction already used for make took recall
        from 65% to 100%. This section checks whether that jump is real
        and provable, or something that could have happened by chance.
      </p>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="border border-zinc-200 rounded-md p-3">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">Before</div>
          <div className="font-mono text-2xl text-zinc-900">{(before.recall * 100).toFixed(2)}%</div>
          <div className="text-xs text-zinc-500">{before.caught} of {before.n} caught</div>
        </div>
        <div className="border border-zinc-200 rounded-md p-3">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">After</div>
          <div className="font-mono text-2xl text-emerald-700">{(after.recall * 100).toFixed(2)}%</div>
          <div className="text-xs text-zinc-500">{after.caught} of {after.n} caught</div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mb-2">
          Same 20 auctions, before and after
        </div>
        <table className="text-sm font-mono border border-zinc-200 rounded-md overflow-hidden w-full">
          <tbody>
            <tr className="border-b border-zinc-200">
              <td className="p-2 text-zinc-500 text-xs">caught both times</td>
              <td className="p-2 text-right">{contingencyTable[0][0]}</td>
            </tr>
            <tr className="border-b border-zinc-200">
              <td className="p-2 text-zinc-500 text-xs">missed then caught</td>
              <td className="p-2 text-right text-emerald-700">{contingencyTable[1][0]}</td>
            </tr>
            <tr className="border-b border-zinc-200">
              <td className="p-2 text-zinc-500 text-xs">caught then missed</td>
              <td className="p-2 text-right">{contingencyTable[0][1]}</td>
            </tr>
            <tr>
              <td className="p-2 text-zinc-500 text-xs">missed both times</td>
              <td className="p-2 text-right">{contingencyTable[1][1]}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <span className="text-sm text-zinc-700">
          McNemar's exact test, p = <span className="font-mono">{pValue}</span>, significant
        </span>
        <TooltipWrapper label="Fisher vs McNemar">
          <p className="mb-2">
            An earlier version of this check used Fisher's exact test, which assumes two
            independent groups. That gave p = {correctionNote.wrongP}.
          </p>
          <p className="mb-2">
            This is actually paired data, the same 20 auctions measured twice, so it needed{' '}
            {correctionNote.correctTest} instead. That gives p = {correctionNote.correctP}.
          </p>
          <p>{correctionNote.note}</p>
        </TooltipWrapper>
      </div>

      <TakeawayBadge
        measures="Whether the drivetrain fix's recall jump from 65% to 100% could be explained by chance."
        pattern="Only 7 of the 20 auctions actually flipped from missed to caught, and none flipped the other way."
        soWhat={powerNote}
      />
    </Card>
  )
}
