import type { Usage } from './api'

// Swiss formatting: 1’000 and 0.02
const tokens = new Intl.NumberFormat('de-CH')
const cents = new Intl.NumberFormat('de-CH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const small = new Intl.NumberFormat('de-CH', { maximumSignificantDigits: 2 })

export function formatTokens(count: number): string {
  return tokens.format(count)
}

/** Estimated cost like "~0.02 $"; amounts below a cent keep two significant digits. */
export function formatCost(usd: number | null): string {
  if (usd === null) return '– $'
  const amount = usd === 0 || usd >= 0.01 ? cents.format(usd) : small.format(usd)
  return `~${amount} $`
}

/** Meta line under an answer, e.g. "gpt-5.5 · 1’000 → 500 Tokens · ~0.02 $". */
export function formatUsage(usage: Usage): string {
  const counts = `${formatTokens(usage.input_tokens)} → ${formatTokens(usage.output_tokens)} Tokens`
  return `${usage.model} · ${counts} · ${formatCost(usage.cost_usd)}`
}
