import { useState } from 'react'
import type { FormEvent } from 'react'

const EXAMPLES = [
  'What is the minimum height for a guardrail on a residential deck?',
  'Do I need a smoke alarm in every bedroom?',
  'How wide does an exit stair in a house need to be?',
  'What is the minimum ceiling height in a basement?',
]

interface Props {
  loading: boolean
  useRerank: boolean
  onToggleRerank: (value: boolean) => void
  onAsk: (question: string) => void
}

export function AskPanel({ loading, useRerank, onToggleRerank, onAsk }: Props) {
  const [question, setQuestion] = useState('')
  const ready = question.trim().length >= 3 && !loading

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (ready) onAsk(question.trim())
  }

  const askExample = (q: string) => {
    setQuestion(q)
    if (!loading) onAsk(q)
  }

  return (
    <section className="ask-panel" aria-label="Ask a question">
      <form className="ask-form" onSubmit={submit}>
        <label className="sr-only" htmlFor="question">
          Building-code question
        </label>
        <input
          id="question"
          className="ask-input"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask the Code — e.g. minimum guardrail height for a deck?"
          maxLength={500}
          autoFocus
          autoComplete="off"
        />
        <button className="ask-submit" type="submit" disabled={!ready}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden /> Searching…
            </>
          ) : (
            'Ask the Code'
          )}
        </button>
      </form>

      <div className="ask-row">
        <div className="examples" aria-label="Example questions">
          {EXAMPLES.map((q) => (
            <button key={q} type="button" className="example-chip" onClick={() => askExample(q)} disabled={loading}>
              {q}
            </button>
          ))}
        </div>
        <label className="rerank-toggle">
          <span className="rerank-label">
            Rerank<span className="rerank-hint"> · second-stage reordering</span>
          </span>
          <input
            type="checkbox"
            role="switch"
            checked={useRerank}
            onChange={(e) => onToggleRerank(e.target.checked)}
            disabled={loading}
          />
          <span className="switch" aria-hidden />
        </label>
      </div>
    </section>
  )
}
