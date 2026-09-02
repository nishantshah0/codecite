/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Origin of a remotely hosted API, e.g. https://codecite.example.com. Empty = same origin. */
  readonly VITE_API_BASE?: string
  /** "1" builds the static demo: /api calls are answered from public/demo snapshots. */
  readonly VITE_DEMO?: string
  /** Public path the build is served from, e.g. /codecite/ on GitHub Pages. */
  readonly VITE_BASE_PATH?: string
}
