// Source: PROJECT_DEEP_DIVE.md / CLAUDE.md pipeline description.
// type is 'llm' | 'deterministic' | 'hybrid'.

export const PIPELINE_STAGES = [
  {
    id: 'extraction',
    order: 1,
    name: 'Extraction',
    module: 'agents/extraction_agent.py',
    type: 'llm',
    summary: 'Reads the raw listing text and turns it into structured data. Year, make, mileage, VIN, engine, all pulled out with Claude and Instructor.',
    detail:
      'This is the only place in the pipeline where the model reads free text. Everything downstream works off the structured fields it produces.',
  },
  {
    id: 'vin_decode',
    order: 2,
    name: 'VIN decode',
    module: 'agents/vin_agent.py',
    type: 'deterministic',
    summary: 'Looks up the VIN against the free NHTSA government database. No AI involved at all.',
    detail:
      'This is a straight API call. It gives you the real factory spec for that VIN, which is what the extracted listing gets checked against.',
  },
  {
    id: 'photo_analysis',
    order: 3,
    name: 'Photo analysis',
    module: 'agents/photo_agent.py',
    type: 'hybrid',
    summary: 'Claude vision looks at each photo for color, damage, and angle coverage, running in parallel across all photos.',
    detail:
      'Duplicate photo detection runs alongside this and is fully deterministic, a perceptual hash comparison with no model call at all.',
  },
  {
    id: 'verification',
    order: 4,
    name: 'Verification',
    module: 'core/verifier.py',
    type: 'deterministic',
    summary: 'Plain Python rules compare everything the earlier stages found. No LLM call happens here at all.',
    detail:
      'This is the single most important decision in the whole system. A rule either fires or it does not, every time, on the same input. This lets you double-check the results on this page instead of just hoping they make sense.',
    highlight: true,
  },
  {
    id: 'synthesis',
    order: 5,
    name: 'Synthesis',
    module: 'agents/synthesis_agent.py',
    type: 'hybrid',
    summary: 'Deterministic rules turn the flags into a score and an action. The model only writes the human readable summary paragraph.',
    detail:
      'If nothing was flagged, the summary step is skipped entirely and costs nothing.',
  },
]
