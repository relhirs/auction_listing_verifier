// Plain hex duplicates of the Tailwind @theme tokens in src/index.css.
// Recharts renders raw SVG and can't read Tailwind classes, so chart
// stroke/fill props need real hex values. Keep these two files in sync
// by hand if the palette ever changes.

export const CHART_PRIMARY = '#3B5BDB' // cobalt blue - main series
export const CHART_BENCHMARK = '#71717A' // slate gray - baselines, uninformative
export const CHART_ERROR = '#A0522D' // deep terracotta - overconfident / error states
export const CHART_VERIFIED = '#047857' // muted emerald - verified catches

export const ACCENT = '#D97706' // amber-600
export const ACCENT_STRONG = '#B45309'

export const INK = '#18181B'
export const INK_MUTED = '#71717A'
export const BORDER = '#E4E4E7'
export const SURFACE = '#FFFFFF'

// Status color mapping used across Badge, calibration charts, economics table
export const STATUS_COLORS = {
  reliable: CHART_VERIFIED,
  well_calibrated: CHART_VERIFIED,
  ok: CHART_PRIMARY,
  overconfident: CHART_ERROR,
  thin_sample: CHART_BENCHMARK,
  few_positive_examples: CHART_BENCHMARK,
  reverted: CHART_ERROR,
  artifact: CHART_BENCHMARK,
  llm: ACCENT,
  deterministic: CHART_BENCHMARK,
  hybrid: CHART_PRIMARY,
}
