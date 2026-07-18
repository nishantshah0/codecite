export function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`
}

export function formatScore(score: number): string {
  return score.toFixed(3)
}

export function formatCount(n: number): string {
  return n.toLocaleString('en-CA')
}
