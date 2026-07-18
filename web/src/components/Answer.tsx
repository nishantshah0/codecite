import { useMemo, useState } from 'react'

import type { AskResponse } from '../api'
import { segmentAnswer } from '../lib/cite'
import { CheckIcon, CopyIcon } from '../icons'

interface Props {
  result: AskResponse
  activeSource: number | null
  onSelectSource: (index: number) => void
}

export function Answer({ result, activeSource, onSelectSource }: Props) {
  const segments = useMemo(() => segmentAnswer(result.answer, result.citations), [result])
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    const labels = [...new Set(result.citations.flatMap((c) => c.sources))].map(
      (i) => `[${i + 1}] ${result.hits[i].label}`,
    )
    await navigator.clipboard.writeText(`${result.answer}\n\n${labels.join('\n')}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <article className="answer">
      <div className="answer-top">
        <h2 className="answer-question">{result.question}</h2>
        <button className="ghost-button" type="button" onClick={copy} aria-label="Copy answer with citations">
          {copied ? <CheckIcon /> : <CopyIcon />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <p className="answer-text">
        {segments.map((seg, i) =>
          seg.sources.length > 0 ? (
            <button
              key={i}
              type="button"
              className={`cite${seg.sources.includes(activeSource ?? -1) ? ' is-active' : ''}`}
              onClick={() => onSelectSource(seg.sources[0])}
              title={seg.sources.map((s) => result.hits[s]?.label ?? `Source ${s + 1}`).join('\n')}
            >
              {seg.text}
              <sup className="cite-refs">{seg.sources.map((s) => s + 1).join(',')}</sup>
            </button>
          ) : (
            <span key={i}>{seg.text}</span>
          ),
        )}
      </p>
      {result.citations.length === 0 && (
        <p className="answer-note">The model returned no span-level citations for this answer.</p>
      )}
    </article>
  )
}
