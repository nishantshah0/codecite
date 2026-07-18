import type { Health } from '../api'
import { formatCount } from '../lib/format'
import { GitHubIcon, MoonIcon, SunIcon } from '../icons'

interface Props {
  health: Health | null
  healthError: string | null
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}

export function Header({ health, healthError, theme, onToggleTheme }: Props) {
  return (
    <header className="header">
      <div className="header-brand">
        <span className="brand-mark" aria-hidden>
          §
        </span>
        <div>
          <p className="brand-name">
            Code<span className="brand-accent">Cite</span>
          </p>
          <p className="brand-tagline">Clause-cited answers from the National Building Code of Canada 2020</p>
        </div>
      </div>
      <div className="header-side">
        {health && (
          <span className="status-chip" title={`${health.backend} · exact cosine search`}>
            <span className="status-dot ok" aria-hidden />
            {formatCount(health.chunks)} clauses indexed
          </span>
        )}
        {healthError && (
          <span className="status-chip offline">
            <span className="status-dot bad" aria-hidden />
            API offline
          </span>
        )}
        <a
          className="icon-button"
          href="https://github.com/nishantshah0/codecite"
          target="_blank"
          rel="noreferrer"
          aria-label="View CodeCite on GitHub"
        >
          <GitHubIcon width={18} height={18} />
        </a>
        <button
          className="icon-button"
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? <SunIcon width={18} height={18} /> : <MoonIcon width={18} height={18} />}
        </button>
      </div>
    </header>
  )
}
