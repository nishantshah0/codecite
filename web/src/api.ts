// Types mirror codecite/server.py responses.

export interface Models {
  embed: string
  rerank: string
  chat: string
}

export interface Health {
  status: string
  chunks: number
  backend: string
  retrieve_k: number
  rerank_k: number
  models: Models
}

export interface CitationSpan {
  text: string
  start: number | null
  end: number | null
  sources: number[] // indices into AskResponse.hits
}

export interface ChunkHit {
  id: string
  kind: 'article' | 'note'
  division: string
  clause_id: string
  title: string
  page: number
  label: string
  context: string
  text: string
  score: number
  dense_rank: number | null
  dense_score: number | null
}

export interface AskResponse {
  question: string
  use_rerank: boolean
  answer: string
  citations: CitationSpan[]
  hits: ChunkHit[]
  timings_ms: Record<string, number>
  corpus_size: number
  retrieved: number
  models: Models
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, init)
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // non-JSON error body; keep the status line
    }
    throw new Error(detail)
  }
  return resp.json() as Promise<T>
}

export function fetchHealth(): Promise<Health> {
  return request<Health>('/api/health')
}

export function fetchAnswer(question: string, useRerank: boolean): Promise<AskResponse> {
  return request<AskResponse>('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, use_rerank: useRerank }),
  })
}
