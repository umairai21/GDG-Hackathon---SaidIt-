import { useState } from 'react'
import { api } from './api.js'
import TokenChip from './TokenChip.jsx'

const EXAMPLES = ['dahi 1kg', '3eish', 'karak chai', 'chawal basmati 5 kilo', 'leban', 'zaitoon ka tel', 'الحليب ٢ لتر', 'nihari']

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [compare, setCompare] = useState(false)
  const [notice, setNotice] = useState(null)

  async function run(q) {
    setQuery(q)
    setNotice(null)
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    try {
      setData(await api.search(q))
    } catch (e) {
      setError(`Could not reach the search API. Is the backend running? (${e.message})`)
    } finally {
      setLoading(false)
    }
  }

  async function onClick(product) {
    const res = await api.click(data.query, product.id)
    if (res.confirmations.length) {
      const list = res.confirmations.map((c) => `"${c.token}" → ${c.concept}`).join(', ')
      setNotice(`Thanks. Your click was recorded as a confirmation for ${list}. The store decides whether search uses it.`)
    } else {
      setNotice(`Opened ${product.name_en}.`)
    }
  }

  async function onNotWhatIMeant() {
    await api.notWhatIMeant(data.query)
    setNotice('Thanks. We logged that this reading was wrong, and the store will see it on its dashboard.')
  }

  const unsure = data?.tokens.some((t) => t.confidence !== 'sure' && t.role !== 'filler')

  return (
    <div className="space-y-5">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          run(query)
        }}
        className="flex gap-2"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the way you'd say it: dahi, 3eish, حليب, karak chai…"
          className="flex-1 rounded-lg border border-stone-300 bg-white px-4 py-3 text-lg outline-none focus:border-stone-900"
          dir="auto"
        />
        <button className="rounded-lg bg-stone-900 px-5 text-white font-medium">Search</button>
      </form>

      <div className="flex flex-wrap gap-2 text-sm">
        <span className="text-stone-500">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => run(ex)}
            className="rounded-full border border-stone-300 bg-white px-3 py-1 hover:border-stone-900"
            dir="auto"
          >
            {ex}
          </button>
        ))}
      </div>

      {error && <div className="rounded-lg bg-red-50 p-3 text-red-800">{error}</div>}
      {loading && <div className="text-stone-500">Searching…</div>}

      {data && !loading && (
        <>
          <section className="rounded-xl border border-stone-200 bg-white p-4 space-y-3">
            <div className="text-xs font-medium uppercase tracking-wide text-stone-500">How we read your search</div>
            <div className="flex flex-wrap gap-2">
              {data.tokens.map((t, i) => (
                <TokenChip key={i} token={t} />
              ))}
              {data.quantity && (
                <span className="self-center text-sm text-stone-500">· size wanted: {data.quantity.display}</span>
              )}
            </div>
            <div className="space-y-0.5 text-stone-700">
              {data.summary.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <button onClick={onNotWhatIMeant} className="text-stone-600 underline hover:text-stone-900">
                Not what you meant?
              </button>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} />
                Show what a normal store search returns
              </label>
              <span className="text-xs text-stone-400">🟢 sure · 🟡 guessed · 🔴 unknown (hover a word for details)</span>
            </div>
          </section>

          {notice && <div className="rounded-lg bg-sky-50 p-3 text-sm text-sky-900">{notice}</div>}

          <div className={compare ? 'grid gap-6 md:grid-cols-2' : ''}>
            <Results
              title={compare ? 'What You Meant' : null}
              subtitle={unsure ? 'Some words were guessed, so check the chips above.' : null}
              results={data.results}
              onClick={onClick}
              empty="No products match the words we understood. We didn't swap in something else."
            />
            {compare && (
              <Results
                title="A normal store search (fuzzy matching)"
                subtitle="It never says it is unsure. The closest name wins, even when it's a different product."
                results={data.baseline_results}
                onClick={null}
                empty="No results. This is where the customer leaves."
                muted
              />
            )}
          </div>
        </>
      )}
    </div>
  )
}

function Results({ title, subtitle, results, onClick, empty, muted }) {
  return (
    <section className="space-y-2">
      {title && <h2 className="font-semibold">{title}</h2>}
      {subtitle && <p className="text-sm text-stone-500">{subtitle}</p>}
      {results.length === 0 && <div className="rounded-lg border border-dashed border-stone-300 p-6 text-center text-stone-500">{empty}</div>}
      <ul className="grid gap-2 sm:grid-cols-2">
        {results.map((p) => (
          <li key={p.id}>
            <button
              onClick={onClick ? () => onClick(p) : undefined}
              disabled={!onClick}
              className={`w-full text-left rounded-lg border p-3 ${
                muted ? 'border-stone-200 bg-stone-100' : 'border-stone-200 bg-white hover:border-stone-900'
              }`}
            >
              <div className="font-medium">{p.name_en}</div>
              <div className="text-sm text-stone-500" dir="rtl">{p.name_ar}</div>
              <div className="mt-1 flex flex-wrap gap-1 text-xs">
                <span className={`rounded px-1.5 py-0.5 ${p.size_match ? 'bg-emerald-100 text-emerald-800' : 'bg-stone-100 text-stone-600'}`}>
                  {p.size}
                </span>
                <span className="rounded bg-stone-100 px-1.5 py-0.5 text-stone-600">{p.category}</span>
                {p.matched_concepts?.map((c) => (
                  <span key={c} className="rounded bg-sky-50 px-1.5 py-0.5 text-sky-800">matched: {c}</span>
                ))}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
