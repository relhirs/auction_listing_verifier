For more details on this project, click [here](explore_further.md).

# Listing Checker

Catching 9 in 10 auction mistakes before anyone bids.

This is a multi agent AI system that checks used car auction listings before they go live. It reads the seller's description, decodes the VIN, looks at the photos, and cross checks everything against everything else. If the claimed year does not match what the VIN says, if the color in the photos does not match the seller's claim, if the mileage does not add up against the car's own service history, if photos are duplicated or a standard angle is missing, it catches it and tells you why.

I built this, tested it against 500 real closed auctions from Cars and Bids, and measured exactly how well it works. This document walks through what it does, how it works, what the numbers actually showed, and what broke along the way.

[**Live Dashboard**](https://listing-checker-ai.vercel.app/): the full interactive breakdown of every result down below 

## The problem

Cars and Bids is a used car auction site. Before a listing goes live, someone has to check that the seller's claims are actually true. Right now a human editor does that by eye. That works, but it does not scale, and people miss things.

This project asks a simple question. Can a system catch the same mistakes a sharp human editor would catch automatically, and can you actually prove it works instead of just claiming it does.

## How it works

A listing goes through five stages.

1. **Extraction.** An LLM reads the raw listing text and pulls out structured fields like year, make, mileage, VIN, and engine specs.
2. **VIN decode.** The VIN gets sent to the free NHTSA government database, which decodes the factory specs for that exact car. No AI involved here, it's just a lookup.
3. **Photo analysis.** Every photo gets analyzed in parallel by a vision model, checking for things like exterior color and duplicate images.
4. **Verification.** Every field from every source above gets cross checked against every other source. Does the claimed year match the VIN? Does the claimed color match what the photos show? Is the mileage consistent with the car's own documented history? This step produces a list of flags.
5. **Synthesis.** The flags get turned into a final report, a score from 0 to 1, and a recommended action: approve, needs review, or reject.

The full pipeline can run live, end to end. The demo below skips that and replays cached results instead, so trying it never costs anyone real API money.

### Why the verification step is not an LLM

This is the one decision in this whole project I would defend hardest. Step 4, the actual judgment of "does this match or not," is plain deterministic code. No model call happens inside it at all.

An LLM would be more flexible. It could handle different phrasings without anyone writing extra rules. But it would also be non deterministic, meaning the same input could get flagged one day and not the next, and it would be much harder to explain why something got flagged. For a system whose whole job is catching mistakes before they cost someone money, I decided consistency and the ability to point at exactly why something got flagged mattered more than flexibility. AI still handles the rest of the pipeline (extraction, vision, and summarization), just not the actual judgment call. 

One honest note here. Every numeric threshold this verifier uses, like a 5,000 mile tolerance before mileage counts as inconsistent, or a 0.2 liter tolerance on engine size, is a judgment call I made, not something derived from a study. 

## The Benchmark 

To test the system against real-world patterns, I scraped 500 closed auctions and their comment sections, where community members frequently catch errors post-launch. I planted one deliberate, known error into each listing and ran the actual system against it blind to see what it caught and what it missed.

That scraper reverse engineers the site's internal signing scheme to pull real data legitimately and caches everything locally, so nothing gets scraped twice. That part alone was its own small engineering project.

A full writeup can be found [here](explore_further.md).

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

Note: the system works in real time. For this demo, results are cached to avoid API costs. 
```