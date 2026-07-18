import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

const base = (props: IconProps): IconProps => ({
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  ...props,
})

export const GitHubIcon = (props: IconProps) => (
  <svg {...base(props)} fill="currentColor" stroke="none">
    <path d="M12 1.75A10.25 10.25 0 0 0 8.76 21.73c.51.1.7-.22.7-.49l-.01-1.73c-2.85.62-3.45-1.37-3.45-1.37-.47-1.19-1.14-1.5-1.14-1.5-.93-.64.07-.63.07-.63 1.03.07 1.57 1.06 1.57 1.06.91 1.57 2.4 1.11 2.98.85.1-.66.36-1.11.65-1.37-2.28-.26-4.67-1.14-4.67-5.07 0-1.12.4-2.03 1.05-2.75-.1-.26-.46-1.3.1-2.71 0 0 .86-.28 2.82 1.05a9.83 9.83 0 0 1 5.14 0c1.96-1.33 2.82-1.05 2.82-1.05.56 1.41.2 2.45.1 2.71.65.72 1.05 1.63 1.05 2.75 0 3.94-2.4 4.8-4.68 5.06.37.31.69.94.69 1.9l-.01 2.8c0 .27.19.6.71.49A10.25 10.25 0 0 0 12 1.75Z" />
  </svg>
)

export const SunIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2.5M12 19v2.5M4.28 4.28l1.77 1.77M17.95 17.95l1.77 1.77M2.5 12H5M19 12h2.5M4.28 19.72l1.77-1.77M17.95 6.05l1.77-1.77" />
  </svg>
)

export const MoonIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M20.5 14.08A8.5 8.5 0 1 1 9.92 3.5a7 7 0 1 0 10.58 10.58Z" />
  </svg>
)

export const CopyIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" transform="translate(2 2)" />
  </svg>
)

export const CheckIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M4.5 12.5l5 5 10-11" />
  </svg>
)

export const RankUpIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </svg>
)

export const RankDownIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M12 5v14M6 13l6 6 6-6" />
  </svg>
)

export const AlertIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M12 3.5 2.5 20h19L12 3.5ZM12 10v4.5M12 17.5v.5" />
  </svg>
)
