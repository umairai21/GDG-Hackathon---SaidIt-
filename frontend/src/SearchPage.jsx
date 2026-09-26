import { useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import TokenChip, { TokenDetail, isQuiet } from './TokenChip.jsx'
import { Button, CATEGORY_ICON, Card, Icon, Pill } from './ui.jsx'

// Real things people type here. Deliberately not labelled by language: a shopper doesn't care.
const POPULAR = [
  { icon: '🥛', q: 'dahi 1kg' },
  { icon: '🍚', q: 'chawal basmati 5 kilo' },
  { icon: '☕', q: 'karak chai' },
  { icon: '🍞', q: '3eish' },
  { icon: '🥤', q: 'leban' },
  { icon: '🫒', q: 'zaitoon ka tel' },
  { icon: '🥛', q: 'الحليب ٢ لتر' },
  { icon: '🍗', q: 'dajaj' },
]

// Search state lives in the URL (?q=...&compare=1) so a search can be shared or reloaded.
function readUrl() {
  const p = new URLSearchParams(window.location.search)
  return { q: p.get('q') ?? '', compare: p.get('compare') === '1' }
}
function writeUrl(q, compare) {
  const p = new URLSearchParams()
  if (q) p.set('q', q)
  if (compare) p.set('compare', '1')
  window.history.replaceState(null, '', p.toString() ? `/shop?${p}` : '/shop')
}

export default function SearchPage() {
  const initial = readUrl()
  const [query, setQuery] = useState(initial.q)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [compare, setCompare] = useState(initial.compare)
  const [toast, setToast] = useState(null)
  const [pick, setPick] = useState(null) // chosen meaning for an ambiguous word, e.g. "rice"

  useEffect(() => {
    if (initial.q) run(initial.q)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 5000)
    return () => clearTimeout(id)
  }, [toast])

  async function run(q) {
    setQuery(q)
    if (!q.trim()) return
    writeUrl(q, compare)
    setLoading(true)
    setError(null)
    setPick(null)
    try {
      setData(await api.search(q))
    } catch (e) {
      setError(`Couldn't reach the search service. Is the backend running? (${e.message})`)
    } finally {
      setLoading(false)
    }
  }

  function toggleCompare(on) {
    setCompare(on)
    writeUrl(data?.query ?? query, on)
  }

  async function onClick(product) {
    const res = await api.click(data.query, product.id)
    if (res.confirmations.length) {
      const list = res.confirmations.map((c) => `“${c.token}” → ${c.concept}`).join(', ')
      setToast({ title: 'Thanks, that helps', body: `We noted ${list}. The store decides whether search learns it.` })
    } else {
      setToast({ title: product.name_en, body: 'Added to your basket (demo).' })
    }
  }

  async function onNotRight() {
    await api.notWhatIMeant(data.query)
    setToast({ title: 'Thanks for telling us', body: "We've let the store know we read your search wrong." })
  }

  const results = useMemo(
    () => (data && pick ? data.results.filter((r) => r.matched_concepts.includes(pick)) : data?.results ?? []),
    [data, pick],
  )

  return (
    <div className="space-y-6">
      {/* Search box: big welcome before the first search, compact afterwards */}
      <section
        className={`rounded-3xl border border-emerald-100 bg-linear-to-br from-emerald-50 via-white to-sky-50 ${
          data ? 'p-4 sm:p-5' : 'px-5 py-10 sm:px-12 sm:py-14'
        }`}
      >
        {!data && (
          <div className="mx-auto mb-7 max-w-2xl text-center">
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">What are you shopping for?</h1>
            <p className="mt-3 text-slate-600">Type it the way you say it. Any language, any spelling.</p>
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            run(query)
          }}
          className={`flex flex-col gap-2 sm:flex-row ${data ? '' : 'mx-auto max-w-2xl'}`}
        >
          <label className="relative flex-1">
            <span className="sr-only">Search groceries</span>
            <Icon name="search" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for groceries"
              className="w-full rounded-xl border border-slate-300 bg-white py-3.5 pl-12 pr-4 text-lg shadow-sm outline-none transition focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
              dir="auto"
              autoFocus
            />
          </label>
          <Button variant="primary" size="lg" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </Button>
        </form>
      </section>

      {error && (
        <div className="flex items-start gap-2 rounded-xl bg-rose-50 p-4 text-sm text-rose-800 ring-1 ring-rose-200">
          <Icon name="alert" className="mt-0.5 h-4 w-4" /> {error}
        </div>
      )}

      {!data && !error && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-slate-500">Popular right now</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {POPULAR.map((p) => (
              <button
                key={p.q}
                onClick={() => run(p.q)}
                className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-400 hover:shadow-md"
              >
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-2xl">{p.icon}</span>
                <span className="font-medium text-slate-800" dir="auto">{p.q}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {data && (
        <div className={`space-y-5 ${loading ? 'opacity-60' : ''}`}>
          <Understanding data={data} pick={pick} setPick={setPick} onNotRight={onNotRight} />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-slate-500">
              <span className="font-semibold text-slate-900">{results.length}</span> products
            </div>
            <Switch checked={compare} onChange={toggleCompare} label="Compare with a typical store search" />
          </div>

          <div className={compare ? 'grid gap-6 lg:grid-cols-2' : ''}>
            <ResultList
              heading={compare ? 'Our search' : null}
              results={results}
              onClick={onClick}
              compact={compare}
              empty={{
                title: 'No matches',
                body: "We didn't swap your word for something else. The store has been told people are looking for it.",
              }}
            />
            {compare && (
              <ResultList
                heading="Typical store search"
                warning="It never says it's unsure. The closest-looking name wins, even when it's a different product."
                results={data.baseline_results}
                compact
                muted
                empty={{ title: 'No results', body: 'This is where most shoppers give up and leave.' }}
              />
            )}
          </div>
        </div>
      )}

      {toast && (
        <div className="toast-in fixed bottom-6 left-1/2 z-40 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 rounded-xl bg-slate-900 p-4 text-sm text-white shadow-xl">
          <div className="flex items-start gap-3">
            <Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
            <div className="flex-1">
              <div className="font-medium">{toast.title}</div>
              <div className="mt-0.5 text-slate-300">{toast.body}</div>
            </div>
            <button onClick={() => setToast(null)} className="text-slate-400 hover:text-white" aria-label="Dismiss">
              <Icon name="x" className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// What we understood, in shop language. Only draws attention when we're actually unsure;
// the word-by-word technical view is one click away for anyone who wants it.
function Understanding({ data, pick, setPick, onNotRight }) {
  const [showDetails, setShowDetails] = useState(false)
  const [selected, setSelected] = useState(null)
  const words = data.tokens.filter((t) => !isQuiet(t))
  const sure = words.filter((t) => t.confidence === 'sure')
  const guessed = words.filter((t) => t.confidence === 'guessed' && t.concepts.length <= 1)
  const ambiguous = words.filter((t) => t.confidence === 'guessed' && t.concepts.length > 1)
  const unknown = words.filter((t) => t.confidence === 'unknown')

  // "Showing results for yogurt · basmati · 1 kg": what we're confident about
  const understood = [
    ...new Set([
      ...sure.flatMap((t) => (t.role === 'keyword' ? [t.keyword] : t.concept_labels)),
      ...guessed.flatMap((t) => (t.role === 'keyword' ? [t.keyword] : t.concept_labels)),
    ]),
  ]

  return (
    <Card className="overflow-hidden">
      <div className="p-4 sm:p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <p className="text-lg text-slate-700">
            {understood.length ? (
              <>
                Showing results for{' '}
                {understood.map((u, i) => (
                  <span key={u}>
                    {i > 0 && <span className="text-slate-300"> · </span>}
                    <span className="font-semibold text-slate-900">{u}</span>
                  </span>
                ))}
                {data.quantity && <span className="text-slate-500"> · {data.quantity.display}</span>}
              </>
            ) : ambiguous.length ? (
              'Showing both possible meanings'
            ) : (
              "We couldn't match your search"
            )}
          </p>
          <span className="text-sm text-slate-400">
            you searched <span className="text-slate-600" dir="auto">“{data.query}”</span>
          </span>
        </div>

        {(guessed.length > 0 || ambiguous.length > 0 || unknown.length > 0) && (
          <div className="mt-4 space-y-2">
            {guessed.map((t, i) => (
              <Notice key={`g${i}`} tone="amber" icon="info">
                We think <b dir="auto">“{t.original}”</b> means{' '}
                <b>{t.role === 'keyword' ? t.keyword : t.concept_labels[0]}</b>.{' '}
                <button onClick={onNotRight} className="font-medium underline underline-offset-2 hover:text-amber-950">
                  Not right?
                </button>
              </Notice>
            ))}
            {ambiguous.map((t, i) => (
              <Notice key={`a${i}`} tone="amber" icon="info">
                <div>
                  <b dir="auto">“{t.original}”</b> can mean {t.concept_labels.join(' or ')}, depending on where you're
                  from. Which one?
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Choice active={!pick} onClick={() => setPick(null)}>Show both</Choice>
                  {t.concepts.map((c, j) => (
                    <Choice key={c} active={pick === c} onClick={() => setPick(c)}>
                      {t.concept_labels[j]}
                    </Choice>
                  ))}
                </div>
              </Notice>
            ))}
            {unknown.map((t, i) => (
              <Notice key={`u${i}`} tone="rose" icon="alert">
                We don't know <b dir="auto">“{t.original}”</b> yet, so we didn't replace it with a guess. We've let the
                store know.
              </Notice>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => setShowDetails((s) => !s)}
        className="flex w-full items-center justify-between border-t border-slate-100 bg-slate-50/70 px-4 py-2.5 text-left text-sm text-slate-500 hover:text-slate-800 sm:px-5"
      >
        <span className="inline-flex items-center gap-2">
          <Icon name="sparkle" className="h-4 w-4" /> How we read your search
        </span>
        <span className={`transition ${showDetails ? 'rotate-90' : ''}`}>
          <Icon name="arrow" className="h-4 w-4" />
        </span>
      </button>

      {showDetails && (
        <div className="fade-in space-y-3 border-t border-slate-100 p-4 sm:p-5">
          <p className="text-sm text-slate-500">
            Each word, and how sure we were. Tap a word to see the steps.
          </p>
          <div className="flex flex-wrap gap-2">
            {data.tokens.map((t, i) => (
              <TokenChip key={i} token={t} selected={selected === i} onSelect={() => setSelected(selected === i ? null : i)} />
            ))}
          </div>
          {selected != null && data.tokens[selected] && <TokenDetail token={data.tokens[selected]} />}
        </div>
      )}
    </Card>
  )
}

function Notice({ tone, icon, children }) {
  const tones = {
    amber: 'bg-amber-50 text-amber-900 ring-amber-200',
    rose: 'bg-rose-50 text-rose-900 ring-rose-200',
  }
  return (
    <div className={`flex gap-2.5 rounded-xl p-3 text-sm ring-1 ring-inset ${tones[tone]}`}>
      <Icon name={icon} className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function Choice({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-sm font-medium ring-1 ring-inset transition ${
        active ? 'bg-amber-900 text-white ring-amber-900' : 'bg-white text-amber-900 ring-amber-300 hover:ring-amber-500'
      }`}
    >
      {children}
    </button>
  )
}

function Switch({ checked, onChange, label }) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-3 text-sm font-medium text-slate-600">
      <span className="relative">
        <input type="checkbox" className="peer sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className="block h-6 w-11 rounded-full bg-slate-300 transition peer-checked:bg-emerald-600 peer-focus-visible:ring-4 peer-focus-visible:ring-emerald-100" />
        <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition peer-checked:translate-x-5" />
      </span>
      {label}
    </label>
  )
}

function ResultList({ heading, warning, results, onClick, compact, muted, empty }) {
  return (
    <section className="space-y-3">
      {heading && <div className="text-sm font-semibold text-slate-900">{heading}</div>}
      {warning && (
        <div className="flex gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">
          <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0" /> {warning}
        </div>
      )}
      {results.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-10 text-center">
          <Icon name="inbox" className="mx-auto h-8 w-8 text-slate-300" />
          <div className="mt-2 font-medium text-slate-700">{empty.title}</div>
          <div className="mx-auto mt-1 max-w-sm text-sm text-slate-500">{empty.body}</div>
        </div>
      ) : (
        <ul className={`grid gap-3 ${compact ? 'sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2' : 'sm:grid-cols-2 lg:grid-cols-3'}`}>
          {results.map((p) => (
            <li key={p.id}>
              <ProductCard product={p} onClick={onClick} muted={muted} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function ProductCard({ product: p, onClick, muted }) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      onClick={onClick ? () => onClick(p) : undefined}
      className={`group flex h-full w-full gap-3 rounded-2xl border p-3 text-left transition ${
        muted ? 'border-slate-200 bg-slate-50' : 'border-slate-200 bg-white shadow-sm hover:-translate-y-0.5 hover:border-emerald-400 hover:shadow-md'
      }`}
    >
      <div className={`grid h-16 w-16 shrink-0 place-items-center rounded-xl text-3xl ${muted ? 'bg-slate-200/70 grayscale' : 'bg-slate-100'}`}>
        {CATEGORY_ICON[p.category] ?? '🛒'}
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-medium leading-snug text-slate-900">{p.name_en}</div>
        <div className="mt-0.5 truncate text-sm text-slate-500" dir="rtl">{p.name_ar}</div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Pill className={p.size_match ? 'bg-emerald-50 text-emerald-800 ring-emerald-200' : 'bg-white text-slate-600 ring-slate-200'}>
            {p.size_match && <Icon name="check" className="h-3 w-3" />}
            {p.size}
          </Pill>
        </div>
      </div>
    </Tag>
  )
}
