// Small shared UI pieces so both pages look like one product.

export const CONFIDENCE = {
  sure: {
    label: 'Sure',
    dot: 'bg-emerald-500',
    pill: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    chip: 'bg-emerald-50/70 ring-emerald-200 hover:ring-emerald-400',
    selected: 'ring-2 ring-emerald-500 bg-emerald-50',
    text: 'text-emerald-700',
    bar: 'bg-emerald-500',
    help: 'Found exactly in our word lists.',
  },
  guessed: {
    label: 'Guessed',
    dot: 'bg-amber-400',
    pill: 'bg-amber-50 text-amber-800 ring-amber-200',
    chip: 'bg-amber-50/70 ring-amber-200 hover:ring-amber-400',
    selected: 'ring-2 ring-amber-500 bg-amber-50',
    text: 'text-amber-700',
    bar: 'bg-amber-400',
    help: 'Matched after fixing spelling, or the word has more than one meaning.',
  },
  unknown: {
    label: 'Unknown',
    dot: 'bg-rose-500',
    pill: 'bg-rose-50 text-rose-800 ring-rose-200',
    chip: 'bg-rose-50/70 ring-rose-200 hover:ring-rose-400',
    selected: 'ring-2 ring-rose-500 bg-rose-50',
    text: 'text-rose-700',
    bar: 'bg-rose-500',
    help: "We don't know this word, so we kept it as typed and didn't guess.",
  },
}

export const LANGUAGE_LABEL = {
  english: 'English',
  roman_urdu: 'Urdu/Hindi',
  arabizi: 'Arabizi',
  arabic: 'Arabic',
  unknown: 'Unknown',
}
export const languageLabel = (code) =>
  (code || 'unknown').split('+').map((c) => LANGUAGE_LABEL[c] ?? c).join(' · ')

export const CATEGORY_ICON = {
  Dairy: '🥛', Eggs: '🥚', 'Meat & Poultry': '🍗', Fish: '🐟', Rice: '🍚', Bakery: '🍞',
  Flour: '🌾', Pantry: '🫙', Oil: '🫒', Pulses: '🫘', Vegetables: '🥬', Fruit: '🍎',
  Dates: '🌴', 'Tea & Coffee': '☕', Spices: '🌶️', Condiments: '🥫', Beverages: '🥤',
  Snacks: '🍪', Household: '🧼',
}

export function Card({ className = '', children }) {
  return <div className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</div>
}

export function Pill({ className = '', children }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${className}`}>
      {children}
    </span>
  )
}

export function ConfidencePill({ confidence }) {
  const c = CONFIDENCE[confidence]
  return (
    <Pill className={c.pill}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </Pill>
  )
}

export function Button({ variant = 'primary', size = 'md', className = '', ...props }) {
  const variants = {
    primary: 'bg-emerald-700 text-white hover:bg-emerald-800 shadow-sm',
    dark: 'bg-slate-900 text-white hover:bg-slate-800 shadow-sm',
    secondary: 'bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50',
    ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  }
  const sizes = { sm: 'px-2.5 py-1.5 text-xs', md: 'px-3.5 py-2 text-sm', lg: 'px-5 py-3 text-base' }
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
    />
  )
}

export function SectionTitle({ title, subtitle, right }) {
  return (
    <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {right}
    </div>
  )
}

// Minimal inline icon set (no icon-library dependency).
const PATHS = {
  search: 'M21 21l-4.35-4.35M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14z',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  check: 'M5 13l4 4L19 7',
  x: 'M6 6l12 12M18 6L6 18',
  alert: 'M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z',
  info: 'M12 16v-4m0-4h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
  clock: 'M12 7v5l3 3m7-3a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
  chart: 'M4 20V10m6 10V4m6 16v-7m4 7H2',
  inbox: 'M22 12h-6l-2 3h-4l-2-3H2M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
  store: 'M3 9l1.5-5h15L21 9M3 9h18M3 9v11h18V9M9 20v-6h6v6',
  sparkle: 'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z',
  flag: 'M4 22V4m0 0h13l-2 4 2 4H4',
  undo: 'M9 14L4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3',
  scale: 'M12 3v18M5 7h14M5 7l-3 7a4 4 0 0 0 6 0L5 7zm14 0l-3 7a4 4 0 0 0 6 0l-3-7z',
}

export function Icon({ name, className = 'h-4 w-4' }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d={PATHS[name]} />
    </svg>
  )
}
