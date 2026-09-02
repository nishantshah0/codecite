// Types mirror codecite/server.py responses.
//
// Two build-time switches (see vite-env.d.ts):
//   VITE_API_BASE  origin of a remotely hosted API; default same-origin.
//   VITE_DEMO=1    static demo: answer from public/demo snapshots written by
//                  scripts/export_demo.py (GitHub Pages has no backend).

const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')
export const DEMO = import.meta.env.VITE_DEMO === '1'

// Mirrors scripts/dev_server.py: the first topic keyword found in the
// question selects its canned answer, else the fallback.
const DEMO_TOPICS = ['guard', 'smoke', 'stair', 'ceiling']

function demoTopic(question: string): string {
  const q = question.toLowerCase()
  return DEMO_TOPICS.find((t) => q.includes(t)) ?? 'default'
}

function demoUrl(file: string): string {
  return `${import.meta.env.BASE_URL}demo/${file}`
}

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
  if (DEMO) return request<Health>(demoUrl('health.json'))
  return request<Health>(`${API_BASE}/api/health`)
}

export async function fetchAnswer(question: string, useRerank: boolean): Promise<AskResponse> {
  if (DEMO) {
    const file = `ask/${demoTopic(question)}-${useRerank ? 'rerank' : 'dense'}.json`
    const snapshot = await request<AskResponse>(demoUrl(file))
    return { ...snapshot, question }
  }
  return request<AskResponse>(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, use_rerank: useRerank }),
  })
}
