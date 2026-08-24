import Card from '../common/Card'
import Badge from '../common/Badge'
import TooltipWrapper from '../common/TooltipWrapper'
import TakeawayBadge from '../common/TakeawayBadge'
import { LOGISTIC_REGRESSION } from '../../data/logisticRegressionData'

export default function LogisticRegressionDrawer() {
  const lr = LOGISTIC_REGRESSION
  const prosePatch = lr.coefficients.find((c) => c.name === 'prose_patch_applied')

  return (
    <Card title="Did the prose patch fix actually matter?">
      <p className="text-sm text-zinc-600 mb-3">
        The drivetrain section above fixed a self correction bug: a planted lie like "4WD" got
        quietly overwritten back to the truth by the extraction step, before the check ever saw
        it. That same failure can happen for five other error types too, so this project has a
        separate code fix for it called the <span className="font-medium text-zinc-800">prose
        patch</span>. After a fake error is planted in a listing, the patch rewrites the
        surrounding seller description text so it stops describing the real, true version of the
        car, removing the contradiction the extraction step was using to correct itself. It does
        not always successfully apply, since its find-and-replace logic does not match every
        listing's exact wording.
      </p>
      <p className="text-sm text-zinc-600 mb-3">
        Before the drivetrain bugs above were fixed, whether the prose patch had successfully
        applied looked like a real, general predictor of getting an error caught, across every
        error type, statistically significant at p = 0.016. That would have been a solid separate
        finding to report.
      </p>
      <p className="text-sm text-zinc-600 mb-4">
        That pattern was completely wiped out once the drivetrain bugs were fixed. Almost all of
        the original 2.57x came from two categories,{' '}
        <span className="font-mono text-xs">drivetrain_swap</span> and{' '}
        <span className="font-mono text-xs">make_error</span>, the exact same ones root caused and
        fixed to zero real misses in the sections above. Those two categories used to supply most
        of the "patch applied, error got caught" pairs the model was learning the pattern from.
        Once their misses vanished, so did the pattern: what's left is 33 misses spread thinly
        across the four remaining error types, not enough for a real prose patch effect to show up
        on its own. The earlier significant result was never really about the prose patch working.
        It was about drivetrain and make being broken, and the patch data just happened to move
        together with them.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="border border-zinc-200 rounded-md p-3">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
            Before the drivetrain fix
          </div>
          <div className="font-mono text-2xl text-zinc-900">
            {prosePatch.preFix.or.toFixed(2)}x
          </div>
          <div className="text-xs text-zinc-500">
            p = {prosePatch.preFix.p} &middot; significant
          </div>
        </div>
        <div className="border border-zinc-200 rounded-md p-3">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
            After the drivetrain fix
          </div>
          <div className="font-mono text-2xl text-zinc-900">{prosePatch.or.toFixed(2)}x</div>
          <div className="text-xs text-zinc-500">
            p = {prosePatch.p.toFixed(2)} &middot; not significant
          </div>
        </div>
      </div>

      <TooltipWrapper label="Show the full regression table">
        <div className="space-y-3">
          <div className="overflow-x-auto">
            <table className="text-sm w-full min-w-[500px]">
              <thead>
                <tr className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-200">
                  <th className="text-left py-2">Term</th>
                  <th className="text-right py-2">Odds ratio</th>
                  <th className="text-right py-2">95% CI</th>
                  <th className="text-right py-2">p</th>
                </tr>
              </thead>
              <tbody>
                {lr.coefficients.map((c) => (
                  <tr key={c.name} className="border-b border-zinc-100">
                    <td className="py-2 pr-2">{c.name}</td>
                    {c.degenerate ? (
                      <td className="py-2 text-right" colSpan={3}>
                        <Badge variant="artifact">Perfect separation, 100% catch rate</Badge>
                      </td>
                    ) : (
                      <>
                        <td className="py-2 text-right font-mono">{c.or.toFixed(3)}</td>
                        <td className="py-2 text-right font-mono text-xs text-zinc-500">
                          [{c.ciLow.toFixed(2)}, {c.ciHigh === Infinity ? '∞' : c.ciHigh.toFixed(2)}]
                        </td>
                        <td className="py-2 text-right font-mono">{c.p}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-zinc-500">
            Drivetrain and make show "perfect separation" instead of a number: both now catch
            every real case with zero misses left, so there's no variation left for the model to
            explain, and it pushes the coefficient toward infinity trying anyway. That's a
            statistical artifact, not a real effect.
          </p>
          <p className="text-xs text-zinc-500">
            {lr.eventsPerPredictor} real misses per predictor, below the usual rule of thumb of
            10, so treat every coefficient here as a rough read.
          </p>
        </div>
      </TooltipWrapper>

      <div className="mt-4">
        <TakeawayBadge
          pattern="The odds ratio dropped from 2.57 (significant, p = 0.016) to 1.62 (not significant, p = 0.26) once the drivetrain bugs were fixed and their misses left the data."
          soWhat="The real finding here is not the p value, it is catching a confound before shipping it as a real effect. The prose patch is still a real, separate fix. The drivetrain fix is what actually explains the recall jump."
        />
      </div>
    </Card>
  )
}
