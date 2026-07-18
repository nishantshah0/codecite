import type { CitationSpan } from '../api'

// A piece of the answer text: plain, or covered by one citation span.
export interface Segment {
  text: string
  sources: number[]
}

interface Span {
  start: number
  end: number
  sources: number[]
}

/**
 * Split the answer into plain and cited segments.
 *
 * Uses the model's character offsets when present; falls back to searching
 * for the quoted span text (left to right, so repeated phrases attach to
 * successive occurrences). Overlapping spans keep the earlier one — segments
 * must tile the answer exactly, so every character renders exactly once.
 */
export function segmentAnswer(answer: string, citations: CitationSpan[]): Segment[] {
  const spans: Span[] = []
  let searchFrom = 0
  for (const c of citations) {
    let { start, end } = c
    if (start == null || end == null || start < 0 || end > answer.length || start >= end) {
      const at = answer.indexOf(c.text, searchFrom)
      if (at === -1 || c.text.length === 0) continue
      start = at
      end = at + c.text.length
    }
    searchFrom = Math.max(searchFrom, end)
    spans.push({ start, end, sources: c.sources })
  }

  spans.sort((a, b) => a.start - b.start || a.end - b.end)
  const kept: Span[] = []
  for (const s of spans) {
    const last = kept[kept.length - 1]
    if (last && s.start < last.end) continue
    kept.push(s)
  }

  const segments: Segment[] = []
  let cursor = 0
  for (const s of kept) {
    if (s.start > cursor) segments.push({ text: answer.slice(cursor, s.start), sources: [] })
    segments.push({ text: answer.slice(s.start, s.end), sources: s.sources })
    cursor = s.end
  }
  if (cursor < answer.length) segments.push({ text: answer.slice(cursor), sources: [] })
  return segments
}
