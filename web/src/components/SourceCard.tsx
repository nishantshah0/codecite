import { useEffect, useRef } from 'react'

import type { ChunkHit } from '../api'
import { formatScore } from '../lib/format'
import { RankDownIcon, RankUpIcon } from '../icons'

interface Props {
  hit: ChunkHit
  index: number
  cited: boolean
  active: boolean
  reranked: boolean
  onSelect: (index: number) => void
}

export function SourceCard({ hit, index, cited, active, reranked, onSelect }: Props) {
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!active || !ref.current) return
    const el = ref.current
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    const behavior: ScrollBehavior = reduce ? 'auto' : 'smooth'
    const rail = el.closest('.sources')
    if (rail && rail.scrollHeight > rail.clientHeight + 1) {
      // Desktop: the rail scrolls internally so the answer never moves.
      const delta = el.getBoundingClientRect().top - rail.getBoundingClientRect().top
      const target = Math.max(0, rail.scrollTop + delta - (rail.clientHeight - el.offsetHeight) / 2)
      rail.scrollTo({ top: target, behavior })
      if (behavior === 'smooth') {
        // Smooth scrolls are dropped in throttled/background tabs; land anyway.
        const snap = setTimeout(() => {
          if (Math.abs(rail.scrollTop - target) > 32) rail.scrollTo({ top: target })
        }, 500)
        return () => clearTimeout(snap)
      }
    } else {
      el.scrollIntoView({ behavior, block: 'nearest' })
    }
  }, [active])

  const moved = reranked && hit.dense_rank != null ? hit.dense_rank - index : 0

  return (
    <article ref={ref} className={`source${active ? ' is-active' : ''}`} id={`source-${index}`}>
      <header className="source-head">
        <button
          className="source-num"
          type="button"
          onClick={() => onSelect(index)}
          aria-label={`Highlight statements supported by source ${index + 1}`}
        >
          {index + 1}
        </button>
        <span className="source-clause">
          Div. {hit.division} · {hit.kind === 'note' ? 'Note' : 'Art.'} {hit.clause_id}
        </span>
        <span className="source-page">PDF p. {hit.page}</span>
        {cited && <span className="source-cited">cited</span>}
      </header>

      <h3 className="source-title">{hit.title}</h3>

      <div className="source-scores">
        <div
          className="score-bar"
          role="img"
          aria-label={`${reranked ? 'Relevance' : 'Cosine similarity'} ${formatScore(hit.score)}`}
        >
          <span className="score-fill" style={{ width: `${Math.max(4, Math.min(100, hit.score * 100))}%` }} />
        </div>
        <span className="score-value">{formatScore(hit.score)}</span>
        {reranked && moved !== 0 && (
          <span
            className={`rank-move ${moved > 0 ? 'up' : 'down'}`}
            title={`Dense retrieval ranked this #${(hit.dense_rank ?? 0) + 1}; Rerank moved it to #${index + 1}`}
          >
            {moved > 0 ? <RankUpIcon width={12} height={12} /> : <RankDownIcon width={12} height={12} />}
            {Math.abs(moved)}
          </span>
        )}
        {reranked && moved === 0 && hit.dense_rank != null && (
          <span className="rank-move same" title="Rerank kept the dense-retrieval rank">
            =
          </span>
        )}
      </div>

      <details className="source-body">
        <summary>Clause text</summary>
        <p className="source-context">{hit.context}</p>
        <p className="source-text">{hit.text}</p>
      </details>
    </article>
  )
}
