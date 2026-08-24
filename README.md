# Listing Checker

Catching 9 in 10 auction mistakes before anyone bids.

This is a multi agent AI system that checks used car auction listings before they go live. It reads the seller's description, decodes the VIN, looks at the photos, and cross checks everything against everything else. If the claimed year does not match what the VIN says, if the color in the photos does not match the seller's claim, if the mileage does not add up against the car's own service history, if photos are duplicated or a standard angle is missing, it catches it and tells you why.

I built this, tested it against 500 real closed auctions from Cars and Bids, and measured exactly how well it works. This document walks through what it does, how it works, what the numbers actually showed, and what broke along the way.

**Live dashboard:** the full interactive breakdown of every result below lives at [add your Vercel link here once deployed].

## The problem

Cars and Bids is a used car auction site. Before a listing goes live, someone has to check that the seller's claims are actually true. Right now a human editor does that by eye. That works, but it does not scale, and people miss things.

This project asks a simple question. Can a system catch the same mistakes a sharp human editor would catch, automatically, and can you actually prove it works instead of just claiming it does.

## How it works

A listing goes through five stages.

1. **Extraction.** An LLM reads the raw listing text and pulls out structured fields like year, make, mileage, VIN, and engine specs.
2. **VIN decode.** The VIN gets sent to the free NHTSA government database, which decodes the factory specs for that exact car. No AI involved here, it's just a lookup.
3. **Photo analysis.** Every photo gets analyzed in parallel by a vision model, checking for things like exterior color and duplicate images.
4. **Verification.** Every field from every source above gets cross checked against every other source. Does the claimed year match the VIN? Does the claimed color match what the photos show? Is the mileage consistent with the car's own documented history? This step produces a list of flags.
5. **Synthesis.** The flags get turned into a final report, a score from 0 to 1, and a recommended action: approve, needs review, or reject.

A human pastes a listing into the app and gets a report back in under a minute.

### Why the verification step is not an LLM

This is the one decision in this whole project I would defend hardest. Step 4, the actual judgment of "does this match or not," is plain deterministic code. No model call happens inside it at all.

An LLM would be more flexible. It could handle different phrasings without anyone writing extra rules. But it would also be non deterministic, meaning the same input could get flagged one day and not the next, and it would be much harder to explain why something got flagged. For a system whose whole job is catching mistakes before they cost someone money, I decided consistency and the ability to point at exactly why something got flagged mattered more than flexibility. AI still handles the rest of the pipeline (extraction, vision, and summarization), just not the actual judgment call. 

One honest note here. Every numeric threshold this verifier uses, like a 5,000 mile tolerance before mileage counts as inconsistent, or a 0.2 liter tolerance on engine size, is a judgment call I made, not something derived from a study. 

## The Benchmark 

To test the system against real-world patterns, I scraped 500 closed auctions and their comment sections, where community members frequently catch errors post-launch. I planted one deliberate, known error into each listing and ran the actual system against it blind to see what it caught and what it missed.

That scraper reverse engineers the site's internal signing scheme to pull real data legitimately and caches everything locally, so nothing gets scraped twice. That part alone was its own small engineering project.

## What the numbers showed

- **Overall accuracy: 87.50%** (456 of 500 caught), up from 77.50% in the first real run
- **Versus a naive baseline: plus 36 points** (a baseline that just guesses "no error" scores 51.30%)
- **95% confidence interval: [84.51%, 90.34%]**, from 5,000 bootstrap resamples. The headline number is 87.50%, but the honest range is almost six points wide
- **Cost per real catch: about 26 cents**

Most individual checks land at or above 0.94 AUC, meaning the system reliably ranks a real error above a clean listing. One check, engine cylinder mismatches, sits near a coin flip at 0.50 AUC, but that is because there is only one real example of that error in the whole 500 listing set, not because the check itself is bad.

## Real bugs, found and fixed

**The model was correcting my own fake errors.** Early on, the make check was only catching 12.5% of planted errors. I assumed the check itself was broken. It wasn't. The extraction model would notice a fake detail did not match the rest of the listing's own prose and would quietly fix it back to the truth before the check ever got a chance to see it. The bug was in my test setup, not the system. Rewriting the surrounding sentences so the fake detail actually held together fixed it, and recall went to 100%.

**One recall number hid two separate bugs.** The drivetrain check was stuck at 65% recall for a while. It turned out to be two unrelated problems layered on top of each other. First, a stale ground truth file was testing conditions the code had already excluded on purpose. Second, once that was fixed, a real self correction bug remained, the same kind as the make error issue above, just in a different field. Fixing both took recall to 100%.

**A confident sounding fix that made things worse, caught before shipping.** At one point I tried scaling a check's confidence score using how clear the photo evidence looked. It sounded reasonable. It actually dropped 114 real catches below the confidence floor, silently, before anyone saw a flag. A validation pass caught this before it shipped, and the floor logic was fixed to never let that happen again.

**A statistical test that ran fine but was still wrong.** After fixing the drivetrain bug, I first checked whether the improvement was real using Fisher's exact test, which gave a clean p value of 0.0083. That test was the wrong one. Fisher's assumes two independent groups, but this was the same 20 auctions measured twice, before and after. Switching to the correct paired test, McNemar's exact test, gave p = 0.0156. Same conclusion, but now the math actually matches what was measured.

**Confidence that did not know when to be humble.** One check kept reporting high confidence even on its false alarms, all of them the same specific mix up between two drivetrain types. Every other type of mix up it flagged was correct 100% of the time. So confidence for that one specific case got floored down to be more honest, without touching anything that was already working.

## What this does not do

- Mileage checks only work if the listing's own text contains a dated service record, which covers about 72% of real listings. There is no way to check mileage against the VIN directly, mileage is not part of a VIN.
- The real site only sorts photos into five broad categories, not the full list of specific angles a checklist might ideally want.
- Every numeric tolerance in this system is a stated judgment call, not something proven by data. This project measures whether the system behaves consistently with its own rules. It does not independently prove those rules are the objectively correct ones.
- One check, engine cylinder mismatches, has exactly one real example in the entire dataset, so its accuracy number is not meaningful yet either way.
- Listings from before 1981 have VINs too short for the government database to decode a model year at all, so year checks cannot run on those.

## Tech stack

Python, Streamlit for the internal tool, SQLite for storage and logging, Pydantic and Instructor for structured LLM output. Claude for extraction, vision, and summary writing. The free NHTSA VIN decode API. The public facing dashboard is React, Vite, Tailwind, and Recharts.

## Repo layout

- `agents/` the individual pipeline stages, extraction, VIN, photo, editorial, synthesis
- `core/` the deterministic verifier and shared constants
- `corpus/` the scraper that pulls and caches real auction data, plus the hardcoded sample listings and the script that pre-generates their cached demo results
- `eval/` the harness that injects errors and measures what the system catches
  - `real_listing_ground_truth.json` the fake errors planted on top of real listings. This is the answer key the system gets graded against.
  - `results.json` the final scored results across all 500 listings. Almost every chart on the dashboard is built from this one file.
  - `round1_results.json` what extraction, the VIN check, and the photo checks found for each listing, before anything gets scored.
  - `round1_state.json` and `round2_state.json` just bookkeeping for the Anthropic batch API jobs, so a run can pick back up where it left off instead of starting over if it gets interrupted.
  - `round2_local_reports.json` a couple of synthesis reports that ran locally instead of through the batch API, kept as a fallback.
  - `sample_reports_cache.json` pre-run results for the sample listings shown in the live Streamlit demo, so visitors browsing the demo are not triggering real, paid API calls.
  - `results_PRE_DRIVETRAIN_FIX_backup.json` a snapshot of the scores from right before the drivetrain bug got fixed. Kept on purpose, not leftover clutter, since it's what the dashboard uses to prove that fix actually made a measurable difference and was not just luck.
- `analysis/` data science analyses run on top of the eval results, calibration, significance testing, cost breakdowns, all at zero additional cost since they reuse data already collected
- `presentation/app/` the public dashboard you are probably reading this next to
- `app.py` the Streamlit tool a human actually uses

## Running it locally

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```