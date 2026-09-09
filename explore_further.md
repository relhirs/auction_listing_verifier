# Explore further

This is the longer version of the README. If you want to know exactly how the test was built, what actually broke while building this, and the full set of numbers behind the headline, it is all here.

## How I tested it

The checking pipeline is the product. Testing it is a separate thing, built on top of it, whose only job is to answer one question honestly: does this actually catch real problems, and how often.

The first version of this test was a hand typed spreadsheet of about 30 made up listings with fake VINs. Photo checks were faked with a text description standing in for a real image. That proves the pipeline agrees with a world I invented to be easy to check. It proves nothing about real listings, real photos, or real VINs.

So I scraped 500 real, closed Cars and Bids auctions instead. Real cars that actually sold, with real VINs and real photos. Then I took each real listing and changed exactly one thing about it to something false, and wrote down separately what I changed and what it should have been. That written down answer is the ground truth. Everything downstream gets compared against it.

I only ever break one thing per listing, on purpose. If I broke three things and the pipeline only caught two, I would not know which one it missed or why. One error per listing keeps every result mapped to one clean question, did it catch this specific thing.

There are nine kinds of planted errors, matched to what the pipeline is actually supposed to catch: wrong year, wrong make, mileage drift, transmission swap, drivetrain swap, engine mismatch, wrong color, a duplicate photo, and a missing photo category. Which error goes to which listing is assigned round robin, not randomly, so no single error type ends up with an unlucky sample size of one or zero.

Running the real pipeline against 500 doctored listings means thousands of individual AI calls. Doing them one at a time would be slow and more expensive than it needs to be, so the calls go through Anthropic's batch API instead, submitted in bulk and collected later, at half the per call price. Extraction and photo analysis get submitted in one batch since they do not depend on each other. The final summary has to wait for those results first, since it needs to know what was actually flagged, so that step gets submitted separately, afterward.

One subtlety took real digging to find. For year and make errors, a real listing's write up always restates the true year and make in its opening sentence, since that is just how these listings are written. If I only changed the structured year field and left that sentence alone, the fake listing was now telling two different stories, a fake field and true prose sitting right next to it. The AI reading it just believed the prose and reported the real year, so the planted error silently vanished before it ever reached the part of the pipeline meant to catch it. That was not the pipeline failing. It was my own fake error being incomplete. The fix was to rewrite that one sentence too, so the fake listing lies consistently everywhere, the same way an actual fraudulent listing would have to.

A few honest limits are baked into this on purpose. Mileage drift can only be caught if the listing's own text contains a dated service record, which covers about 72% of real listings. There is no way to check mileage against the VIN directly, mileage is not part of a VIN. The real site only sorts photos into five broad categories, not a full checklist of specific angles. And every numeric tolerance the checker uses, like how much mileage drift counts as suspicious, is a stated judgment call I made, not something proven by a study. This test measures whether the pipeline behaves consistently with its own rules. It does not prove those rules are the objectively correct ones.

## What broke, and what I fixed

**The model was quietly correcting my own fake errors.** Early on, the make check was only catching 12.5% of planted errors. I assumed the check was broken. It was not. The extraction model would notice a fake detail did not match the rest of the listing's prose and would fix it back to the truth before the check ever saw it. The bug was in my test setup, not the system. Rewriting the surrounding sentences so the fake detail actually held together fixed it, and recall went to 100%.

**One recall number hid two separate bugs.** The drivetrain check was stuck at 65% recall for a while. It turned out to be two unrelated problems stacked on top of each other. First, a stale ground truth file was testing conditions the code had already ruled out on purpose. Second, once that was fixed, a real self correction bug remained, the same kind as the make error issue, just in a different field. Fixing both took recall to 100%.

**A confidence fix that made things quietly worse, caught before it shipped.** I tried scaling a check's confidence score based on how clear the evidence looked, instead of using one fixed number every time. It sounded reasonable. The first version let confidence drop as low as 0.55, and this project throws away any flag below 0.70 before a human ever sees it. That meant 114 real, correct catches were getting scored low enough to silently vanish, with zero new detections gained anywhere to make up for it. A validation script that reruns the real checker against already collected data caught this before it ever reached real use. The fix guarantees the new formulas can never score below 0.70, no matter what. Rechecked afterward, zero real catches lost.

One part of that same change was tried and then reverted, because it measured worse instead of better. I tried blending in the vision model's own confidence about how clearly it could see a photo into the color check's score. That made the color check's calibration measurably worse, not better, because a vision model being sure it can see a photo clearly has nothing to do with whether a color mismatch is real or a false alarm. So that one piece got reverted back to its original flat number.

**A statistical test that ran cleanly but was still the wrong test.** After fixing the drivetrain bug, I first checked whether the improvement was real using Fisher's exact test, which gave a clean p value of 0.0083. That was the wrong test. Fisher's assumes two independent groups, but this was the same 20 auctions measured twice, before and after. Switching to the correct paired test, McNemar's exact test, gave p equal to 0.0156. Same conclusion, the fix was real, but now the math actually matches what was measured.

**Confidence that did not know when to be humble.** One check kept reporting 90% confidence even on its false alarms, and every single one of those false alarms was the same specific mix up, a listing that said AWD when the VIN said 4WD or the other way around. Every other kind of drivetrain mix up it ever flagged was correct 100% of the time. So I floored that one specific case down to 0.70 instead of dropping it or leaving it at 0.9, since some of the check's real catches are that exact same pair and I did not want to silently throw those away the same way the confidence bug above did.

Along the way I also caught and fixed a handful of smaller bugs that came up while getting the eval right: engine displacement getting a stray digit glued onto it during parsing, boxer and flat engines going unrecognized entirely, automated manual transmissions getting misread as plain manual, comma grouped mileage numbers getting truncated, and a scraper bug that grabbed an entire page's text, comments and all, instead of just the listing's own write up. Each one is a small, ordinary bug, the kind you find by actually reading your own output closely instead of trusting a single summary number.

## The full numbers

The headline: **87% overall verdict accuracy** across 500 real listings, each with one planted error, up from 77% in the first real run.

That is not just a raw catch rate. It means the pipeline's final recommendation, approve, needs review, or reject, matched what the ground truth said it should recommend, on 87 out of every 100 listings tested.

A naive baseline that always guesses "no error" scores 51%, so this is a real 36 point improvement over doing nothing.

That 87% number is also stable, not a fluke of exactly which 500 listings got picked. Running the same measurement 5,000 times on resampled versions of the same data (bootstrap resampling) gives a 95% confidence range of 84% to 90%, about a six point spread. Individual error types range from a recall of 83% (year errors, the hardest category, mostly pre-1981 VINs the government database cannot decode) up to a perfect 100% on drivetrain, make, and mileage errors.

Cost per real catch averages about 13 cents, project wide, out of $60 total spent testing 497 listings. About 7.6% of that spending went to listings where the planted error was never caught at all. The cheapest check per catch is transmission (7 cents), the most expensive is drivetrain (24 cents), mostly because drivetrain errors tend to land on trucks and SUVs with bigger photo sets, which cost more to run through the vision step, not because the check itself is weaker.

Most individual checks land at 0.94 AUC or higher, meaning they reliably rank a real error above a clean listing regardless of where you set the confidence cutoff. One check, engine cylinder mismatches, sits near a coin flip at 0.50, but that is because there is exactly one real example of that error in the whole 500 listing set, not because the check itself is bad.

I also checked whether the 87% headline was only that high because of an easy mix of error types in the test data. I reran the same numbers under a mix weighted by how often each type of problem actually shows up in real Cars and Bids comment threads (24 confirmed, human reviewed cases). Under that real world mix, verdict accuracy comes out even higher, close to 97%, not lower. So the 87% headline is not being flattered by an easy test mix. If anything, real world performance is probably a bit better than the headline number suggests.
