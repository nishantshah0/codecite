import { useCallback, useEffect, useMemo, useState } from 'react'

import { DEMO, fetchAnswer, fetchHealth } from './api'
import type { AskResponse, Health } from './api'
import { Answer } from './components/Answer'
import { AskPanel } from './components/AskPanel'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { PipelineTrace } from './components/PipelineTrace'
import { SourceCard } from './components/SourceCard'
import { AlertIcon, InfoIcon } from './icons'
import { formatCount } from './lib/format'

type Theme = 'light' | 'dark'

export default function App() {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light',
  )
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [useRerank, setUseRerank] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AskResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeSource, setActiveSource] = useState<number | null>(null)

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((e: Error) => setHealthError(e.message))
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  const toggleTheme = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    localStorage.setItem('codecite-theme', next)
  }, [theme])

  const ask = useCallback(
    (question: string) => {
      setLoading(true)
      setError(null)
      setActiveSource(null)
      fetchAnswer(question, useRerank)
        .then(setResult)
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false))
    },
    [useRerank],
  )

  const citedSources = useMemo(
    () => new Set(result?.citations.flatMap((c) => c.sources) ?? []),
    [result],
  )

  return (
    <div className="page">
      <Header health={health} healthError={healthError} theme={theme} onToggleTheme={toggleTheme} />

      <main className="main">
        <AskPanel loading={loading} useRerank={useRerank} onToggleRerank={setUseRerank} onAsk={ask} />

        {DEMO && (
          <div className="notice notice-info" role="status">
            <InfoIcon width={18} height={18} />
            <div>
              <p className="notice-title">Static demo.</p>
              <p className="notice-body">
                This page has no backend: answers are pre-recorded from a synthetic fixture corpus of ten paraphrased
                clauses, not the Code. Questions about guards, stairs, smoke alarms or ceilings match a recorded
                answer, and the Rerank toggle switches between recorded runs. For real answers over all ~3,000 NBC
                clauses, run <code>codecite serve</code> locally.
              </p>
            </div>
          </div>
        )}

        {healthError && (
          <div className="notice" role="alert">
            <AlertIcon width={18} height={18} />
            <div>
              <p className="notice-title">The CodeCite API is not reachable.</p>
              <p className="notice-body">
                Start it with <code>codecite serve</code> (or <code>python scripts/dev_server.py</code> for fixture
                data), then reload.
              </p>
            </div>
          </div>
        )}

        {(result || loading || health) && !healthError && (
          <PipelineTrace health={health} result={result} loading={loading} useRerank={useRerank} />
        )}

        {error && (
          <div className="notice" role="alert">
            <AlertIcon width={18} height={18} />
            <div>
              <p className="notice-title">The pipeline failed on that question.</p>
              <p className="notice-body">{error}</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="columns">
            <div className="skeleton-card answer-skeleton" aria-hidden>
              <span className="skeleton-line w-40" />
              <span className="skeleton-line" />
              <span className="skeleton-line" />
              <span className="skeleton-line w-80" />
            </div>
            <div>
              {[0, 1, 2].map((i) => (
                <div key={i} className="skeleton-card" aria-hidden>
                  <span className="skeleton-line w-40" />
                  <span className="skeleton-line w-80" />
                </div>
              ))}
            </div>
          </div>
        )}

        {result && !loading && (
          <div className="columns">
            <Answer result={result} activeSource={activeSource} onSelectSource={setActiveSource} />
            <section className="sources" aria-label="Retrieved clauses">
              <header className="sources-head">
                <h2>Sources</h2>
                <span className="sources-sub">
                  top {result.hits.length} of {result.retrieved} candidates
                  {result.use_rerank ? ', reranked' : ', dense order'}
                </span>
              </header>
              {result.hits.map((hit, i) => (
                <SourceCard
                  key={hit.id}
                  hit={hit}
                  index={i}
                  cited={citedSources.has(i)}
                  active={activeSource === i}
                  reranked={result.use_rerank}
                  onSelect={setActiveSource}
                />
              ))}
            </section>
          </div>
        )}

        {!result && !loading && !healthError && (
          <section className="hero">
            <h1 className="hero-title">Ask the Building Code.</h1>
            <p className="hero-body">
              Every answer is grounded in the National Building Code of Canada 2020 and cited down to the clause —{' '}
              {health ? formatCount(health.chunks) : 'thousands of'} structure-aware chunks, dense retrieval, a
              rerank stage you can toggle, and span-level citations mapped back to Articles, Sentences and PDF pages.
            </p>
          </section>
        )}
      </main>

      <Footer />
    </div>
  )
}
