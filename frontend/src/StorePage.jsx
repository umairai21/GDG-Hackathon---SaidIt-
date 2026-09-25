import { useEffect, useState } from 'react'
import { api } from './api.js'
import { CONFIDENCE_STYLE } from './TokenChip.jsx'

const STATUS_STYLE = {
  proposed: 'bg-amber-100 text-amber-900',
  approved: 'bg-emerald-100 text-emerald-900',
  removed: 'bg-stone-200 text-stone-600',
  collecting: 'bg-sky-50 text-sky-800',
}

const fmtDate = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function StorePage() {
  const [words, setWords] = useState(null)
  const [log, setLog] = useState([])
  const [evalSummary, setEval] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    try {
      const [w, l] = await Promise.all([api.words(), api.changelog()])
      setWords(w)
      setLog(l)
    } catch (e) {
      setError(`Could not reach the API. Is the backend running? (${e.message})`)
    }
    api.evalSummary().then(setEval).catch(() => setEval(null))
  }
  useEffect(() => {
    load()
  }, [])

  async function decide(id, action) {
    await (action === 'approve' ? api.approve(id) : api.remove(id))
    load()
  }

  if (error) return <div className="rounded-lg bg-red-50 p-3 text-red-800">{error}</div>
  if (!words) return <div className="text-stone-500">Loading…</div>

  const label = (c) => words.concept_labels[c] ?? c
  const lost = words.words.filter((w) => w.lost_sale)
  const proposed = words.mappings.filter((m) => m.status === 'proposed')
  const others = words.mappings.filter((m) => m.status !== 'proposed')

  return (
    <div className="space-y-8">
      <Headline evalSummary={evalSummary} stats={words.stats} lostCount={lost.reduce((n, w) => n + w.zero_result_searches, 0)} />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Proposed mappings: waiting for you</h2>
        <p className="text-sm text-stone-500">
          When {words.confirmations_needed} shoppers confirm a guess by clicking a product, it is proposed here.
          <strong> Search does not use it until you approve it.</strong>
        </p>
        {proposed.length === 0 && <div className="text-sm text-stone-500">Nothing waiting.</div>}
        <div className="grid gap-3 md:grid-cols-2">
          {proposed.map((m) => (
            <div key={m.id} className="rounded-xl border border-amber-300 bg-amber-50 p-4 space-y-2">
              <div className="text-lg">
                <span className="font-semibold">"{m.token}"</span> → {label(m.concept)}
              </div>
              <div className="text-sm text-stone-600">
                {m.count} confirmations · first seen {fmtDate(m.first_seen)}
              </div>
              <div className="text-sm text-stone-600">
                From searches: {m.examples.map((e) => `"${e}"`).join(', ')}
              </div>
              <Conflicts mapping={m} words={words} label={label} />
              <div className="flex gap-2 pt-1">
                <button onClick={() => decide(m.id, 'approve')} className="rounded-md bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white">
                  Approve
                </button>
                <button onClick={() => decide(m.id, 'remove')} className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium">
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Words your customers use that your catalog doesn't know</h2>
        <p className="text-sm text-stone-500">
          Every word that search was unsure about. 🔴 words that keep ending in zero results are probably lost sales.
        </p>
        <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-left text-stone-500">
              <tr>
                <th className="p-3">Word</th>
                <th className="p-3">We currently read it as</th>
                <th className="p-3">Confidence</th>
                <th className="p-3 text-right">Searches</th>
                <th className="p-3 text-right">Zero results</th>
                <th className="p-3 text-right">"Not what I meant"</th>
                <th className="p-3">Learning status</th>
              </tr>
            </thead>
            <tbody>
              {words.words.map((w) => (
                <tr key={w.token} className={`border-t border-stone-100 ${w.lost_sale ? 'bg-red-50' : ''}`}>
                  <td className="p-3 font-medium" dir="auto">
                    {w.token}
                    {w.lost_sale && <span className="ml-2 rounded bg-red-600 px-1.5 py-0.5 text-xs text-white">lost sales</span>}
                  </td>
                  <td className="p-3">
                    {w.concepts.length ? w.concepts.map(label).join(' or ') : w.keyword ? `product word "${w.keyword}"` : '-'}
                    {w.method === 'store_approved' && <span className="ml-1 text-xs text-emerald-700">(approved by you)</span>}
                  </td>
                  <td className="p-3">
                    {CONFIDENCE_STYLE[w.confidence].dot} {w.confidence}
                  </td>
                  <td className="p-3 text-right">{w.searches}</td>
                  <td className="p-3 text-right">{w.zero_result_searches}</td>
                  <td className="p-3 text-right">{w.corrections || ''}</td>
                  <td className="p-3">
                    {w.mappings.length === 0 && <span className="text-stone-400">no clicks yet</span>}
                    {w.mappings.map((m) => (
                      <div key={m.id}>
                        <span className={`rounded px-1.5 py-0.5 text-xs ${STATUS_STYLE[m.status]}`}>
                          {m.status === 'collecting' ? `collecting ${m.count}/${m.needed}` : m.status}
                        </span>{' '}
                        → {label(m.concept)}
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {others.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">All learned mappings</h2>
          <div className="flex flex-wrap gap-2 text-sm">
            {others.map((m) => (
              <div key={m.id} className="flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2">
                <span className={`rounded px-1.5 py-0.5 text-xs ${STATUS_STYLE[m.status]}`}>
                  {m.status === 'collecting' ? `collecting ${m.count}/${m.needed}` : m.status}
                </span>
                "{m.token}" → {label(m.concept)}
                {m.status === 'approved' && (
                  <button onClick={() => decide(m.id, 'remove')} className="text-xs underline text-stone-500">remove</button>
                )}
                {m.status === 'removed' && (
                  <button onClick={() => decide(m.id, 'approve')} className="text-xs underline text-stone-500">re-approve</button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Change log</h2>
        <p className="text-sm text-stone-500">Every change to how search reads words, with who made it. Nothing is hidden.</p>
        <ol className="rounded-xl border border-stone-200 bg-white divide-y divide-stone-100 text-sm">
          {log.length === 0 && <li className="p-3 text-stone-500">No changes yet.</li>}
          {log.map((c) => (
            <li key={c.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 p-3">
              <span className="w-44 shrink-0 text-stone-500">{fmtDate(c.ts)}</span>
              <span className={`rounded px-1.5 py-0.5 text-xs ${STATUS_STYLE[c.action]}`}>{c.action}</span>
              <span>
                "{c.token}" → {label(c.concept)}
              </span>
              <span className="text-stone-500">
                by {c.actor}: {c.detail}
              </span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

// Approving one meaning of an ambiguous word (e.g. 3eish = rice) affects shoppers who meant the
// other one, so show that trade-off right on the card.
function Conflicts({ mapping, words, label }) {
  const w = words.words.find((x) => x.token === mapping.token)
  const alternatives = (w?.concepts ?? []).filter((c) => c !== mapping.concept)
  if (!alternatives.length) return null
  return (
    <div className="rounded bg-white/70 p-2 text-xs text-amber-900">
      Heads up: "{mapping.token}" can also mean {alternatives.map(label).join(' or ')}. Approving this makes search
      always read it as {label(mapping.concept)}.
    </div>
  )
}

function Headline({ evalSummary, stats, lostCount }) {
  const o = evalSummary?.overall
  const card = (value, text, tone = 'text-stone-900') => (
    <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className={`text-2xl font-semibold ${tone}`}>{value}</div>
      <div className="text-sm text-stone-500">{text}</div>
    </div>
  )
  return (
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {card(stats.searches, 'searches in the last 14 days')}
      {card(lostCount, 'searches ended in zero results because of words we did not know', 'text-red-700')}
      {o
        ? card(`${o.fuzzy.zero}% → ${o.ours.zero}%`, 'zero-result rate on our test set: normal fuzzy search vs ours')
        : card('-', 'run eval/run_eval.py to see test results')}
      {o
        ? card(`${o.fuzzy.silent_wrong}% → ${o.ours.silent_wrong}%`, 'wrong product shown with no warning: normal vs ours')
        : card('-', '')}
    </section>
  )
}
