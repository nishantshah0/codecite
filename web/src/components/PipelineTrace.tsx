import type { AskResponse, Health } from '../api'
import { formatCount, formatMs } from '../lib/format'

interface Props {
  health: Health | null
  result: AskResponse | null
  loading: boolean
  useRerank: boolean
}

interface Stage {
  key: string
  name: string
  detail: string
  model?: string
  skipped?: boolean
}

export function PipelineTrace({ health, result, loading, useRerank }: Props) {
  const corpus = result?.corpus_size ?? health?.chunks
  const retrieveK = health?.retrieve_k ?? 30
  const rerankK = health?.rerank_k ?? 8
  const models = result?.models ?? health?.models
  const rerankOn = result ? result.use_rerank : useRerank

  const retrieved = result?.retrieved ?? (corpus ? Math.min(retrieveK, corpus) : retrieveK)

  const stages: Stage[] = [
    { key: 'embed', name: 'Embed', detail: 'query → vector', model: models?.embed },
    {
      key: 'search',
      name: 'Retrieve',
      detail: `${corpus ? formatCount(corpus) : '…'} → ${retrieved} · cosine`,
    },
    {
      key: 'rerank',
      name: 'Rerank',
      detail: rerankOn ? `${retrieved} → ${Math.min(rerankK, retrieved)} · relevance` : 'skipped',
      model: rerankOn ? models?.rerank : undefined,
      skipped: !rerankOn,
    },
    { key: 'generate', name: 'Generate', detail: 'grounded answer + citations', model: models?.chat },
  ]

  const total = result ? Object.values(result.timings_ms).reduce((a, b) => a + b, 0) : null

  return (
    <section className="trace" aria-label="Pipeline trace">
      <ol className={`trace-stages${loading ? ' is-loading' : ''}`}>
        {stages.map((stage, i) => {
          const ms = result?.timings_ms[stage.key]
          return (
            <li key={stage.key} className={`trace-stage${stage.skipped ? ' is-skipped' : ''}`} style={{ ['--i' as string]: i }}>
              <div className="trace-head">
                <span className="trace-name">{stage.name}</span>
                <span className="trace-time">{stage.skipped ? '—' : ms != null ? formatMs(ms) : loading ? '…' : ''}</span>
              </div>
              <span className="trace-detail">{stage.detail}</span>
              {stage.model && <span className="trace-model">{stage.model}</span>}
            </li>
          )
        })}
      </ol>
      <div className="trace-total">
        <span className="trace-total-label">pipeline</span>
        <span className="trace-total-value">{loading ? 'running…' : total != null ? formatMs(total) : 'idle'}</span>
      </div>
    </section>
  )
}
