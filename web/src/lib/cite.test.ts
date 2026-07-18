import { describe, expect, it } from 'vitest'

import type { CitationSpan } from '../api'
import { segmentAnswer } from './cite'

const cite = (partial: Partial<CitationSpan> & { text: string }): CitationSpan => ({
  start: null,
  end: null,
  sources: [0],
  ...partial,
})

describe('segmentAnswer', () => {
  it('splits around a span located by character offsets', () => {
    const answer = 'Guards must be 900 mm high on decks.'
    const segments = segmentAnswer(answer, [
      cite({ text: '900 mm high', start: 15, end: 26, sources: [2] }),
    ])
    expect(segments).toEqual([
      { text: 'Guards must be ', sources: [] },
      { text: '900 mm high', sources: [2] },
      { text: ' on decks.', sources: [] },
    ])
  })

  it('reassembles the exact answer text in order', () => {
    const answer = 'A guard is required. It shall be 1 070 mm high, per the Code.'
    const segments = segmentAnswer(answer, [
      cite({ text: 'required', start: 11, end: 19 }),
      cite({ text: '1 070 mm high', start: 33, end: 46 }),
    ])
    expect(segments.map((s) => s.text).join('')).toBe(answer)
  })

  it('falls back to text search when offsets are missing', () => {
    const answer = 'The limit is 0.70 by mass.'
    const segments = segmentAnswer(answer, [cite({ text: '0.70', sources: [1] })])
    expect(segments[1]).toEqual({ text: '0.70', sources: [1] })
  })

  it('attaches repeated fallback spans to successive occurrences', () => {
    const answer = '900 mm inside, 900 mm outside.'
    const segments = segmentAnswer(answer, [
      cite({ text: '900 mm', sources: [0] }),
      cite({ text: '900 mm', sources: [1] }),
    ])
    const cited = segments.filter((s) => s.sources.length > 0)
    expect(cited).toHaveLength(2)
    expect(segments.map((s) => s.text).join('')).toBe(answer)
  })

  it('drops overlapping and unmatchable spans rather than corrupting the text', () => {
    const answer = 'Stairs shall be 860 mm wide.'
    const segments = segmentAnswer(answer, [
      cite({ text: 'shall be 860', start: 7, end: 19 }),
      cite({ text: 'be 860 mm', start: 13, end: 22 }), // overlaps the first
      cite({ text: 'not in the answer' }),
      cite({ text: 'wide', start: 999, end: 1005 }), // out of range -> falls back to search
    ])
    expect(segments.map((s) => s.text).join('')).toBe(answer)
    expect(segments.filter((s) => s.sources.length > 0)).toHaveLength(2)
  })

  it('returns a single plain segment when there are no citations', () => {
    expect(segmentAnswer('No citations here.', [])).toEqual([
      { text: 'No citations here.', sources: [] },
    ])
  })
})
