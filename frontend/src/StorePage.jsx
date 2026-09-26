import { useEffect, useState } from 'react'
import { api } from './api.js'
import ManagerLogin from './ManagerLogin.jsx'
import { Button, ConfidencePill, Icon, Pill, languageLabel } from './ui.jsx'

// Chart series colours: slots 1 and 2 of the validated default categorical palette
// (checked with the dataviz validator for colour-blind separation and contrast).
const SERIES_OURS = '#2a78d6'
const SERIES_TYPICAL = '#eb6834'

const ACTIVITY = {
  proposed: { text: 'Suggested', dot: 'bg-amber-400' },
  approved: { text: 'Approved', dot: 'bg-emerald-500' },
  removed: { text: 'Dismissed', dot: 'bg-slate-400' },
}
const ACTIVITY_PREVIEW = 5

const TABS = [
  { id: 'all', label: 'All', test: () => true },
  { id: 'unknown', label: 'Unknown', test: (w) => w.confidence === 'unknown' },
  { id: 'guessed', label: 'Guessing', test: (w) => w.confidence === 'guessed' },
  { id: 'learned', label: 'Learned', test: (w) => w.mappings.some((m) => m.status !== 'collecting') },
]

const fmtDate = (iso) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })

export default function StorePage({ onAuthChange = () => {} }) {
  const [words, setWords] = useState(null)
  const [log, setLog] = useState([])
  const [evalSummary, setEval] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)
  const [signedIn, setSignedIn] = useState(null) // null = checking

  async function load() {
    try {
      const [w, l] = await Promise.all([api.words(), api.changelog()])
      setWords(w)
      setLog(l)
      setSignedIn(true)
      onAuthChange(true) // header shows the Dashboard / Customer view switch
    } catch (e) {
      if (e.status === 401) {
        setSignedIn(false) // session expired or never signed in
        onAuthChange(false)
      }
      else setError(`Couldn't reach the API. Is the backend running? (${e.message})`)
    }
    api.evalSummary().then(setEval).catch(() => setEval(null))
  }
  useEffect(() => {
    api
      .me()
      .then((r) => (r.manager ? load() : setSignedIn(false)))
      .catch((e) => setError(`Couldn't reach the API. Is the backend running? (${e.message})`))
  }, [])

  async function signOut() {
    await api.logout()
    onAuthChange(false)
    window.location.assign('/') // back to the start page to choose customer or manager again
  }

  async function decide(id, action) {
    setBusy(id)
    try {
      await (action === 'approve' ? api.approve(id) : api.remove(id))
      await load()
    } finally {
      setBusy(null)
    }
  }

  if (error)
    return (
      <div className="flex items-start gap-2 rounded-xl bg-rose-50 p-4 text-sm text-rose-800 ring-1 ring-rose-200">
        <Icon name="alert" className="mt-0.5 h-4 w-4" /> {error}
      </div>
    )
  if (signedIn === false) return <ManagerLogin onSignedIn={load} />
  if (!words) return <div className="py-20 text-center text-slate-400">Loading…</div>

  const label = (c) => words.concept_labels[c] ?? c
  const proposed = words.mappings.filter((m) => m.status === 'proposed')
  const approved = words.mappings.filter((m) => m.status === 'approved')
  const lost = words.words.filter((w) => w.lost_sale)
  const lostSearches = lost.reduce((n, w) => n + w.zero_result_searches, 0)

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Overview</h1>
          <p className="mt-1 text-sm text-slate-500">What your customers searched for, and what search is learning.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600">
            <Icon name="clock" className="h-4 w-4 text-slate-400" /> Last 14 days
          </span>
          <Button variant="secondary" size="md" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Searches" value={words.stats.searches} caption="all customer searches" />
        <Kpi label="Missed searches" value={lostSearches} caption={`zero results, from ${lost.length} unknown words`} marker="bg-rose-500" />
        <Kpi label="To review" value={proposed.length} caption="suggestions waiting for you" marker="bg-amber-400" />
        <Kpi label="Learned words live" value={approved.length} caption="approved by you, used in search" marker="bg-emerald-500" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Review queue */}
        <Panel
          className="lg:col-span-2"
          title="Suggestions to review"
          count={proposed.length}
          subtitle="Learned from shopper clicks. Search only uses a suggestion after you approve it."
        >
          {proposed.length === 0 ? (
            <Empty icon="check" text="You're all caught up." />
          ) : (
            <ul className="divide-y divide-slate-100">
              {proposed.map((m) => (
                <ReviewRow key={m.id} m={m} words={words} label={label} busy={busy === m.id} onDecide={decide} />
              ))}
            </ul>
          )}
        </Panel>

        {/* Quality chart */}
        <Panel title="Search quality" subtitle={evalSummary ? `Measured on ${evalSummary.n_queries} test searches` : 'Run eval/run_eval.py'}>
          {evalSummary ? <QualityChart overall={evalSummary.overall} /> : <Empty icon="chart" text="No test results yet." />}
        </Panel>

        {/* Missed searches */}
        <Panel
          className="lg:col-span-2"
          title="Top missed searches"
          subtitle="Words that returned no products. Worth stocking, or adding to your catalog."
          right={<span className="text-xs text-slate-500">{lostSearches} searches · {lost.length} words</span>}
        >
          {lost.length === 0 ? <Empty icon="check" text="No missed searches." /> : <MissedBars rows={lost} total={lostSearches} />}
        </Panel>

        {/* Activity */}
        <Panel title="Recent activity" subtitle="Every change to how search reads words.">
          <Activity log={log} approved={approved} label={label} busy={busy} onUndo={(id) => decide(id, 'remove')} />
        </Panel>
      </div>

      <WordTable words={words.words} label={label} />
    </div>
  )
}

// ---------------------------------------------------------------- building blocks

function Panel({ title, subtitle, count, right, className = '', children }) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs ${className}`}>
      <header className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            {title}
            {count != null && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">{count}</span>
            )}
          </h2>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
        </div>
        {right && <div className="shrink-0 pt-0.5">{right}</div>}
      </header>
      {children}
    </section>
  )
}

function Kpi({ label, value, caption, marker }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-xs">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
        {marker && <span className={`h-2 w-2 rounded-full ${marker}`} />}
        {label}
      </div>
      <div className="mt-2 text-3xl font-semibold tracking-tight tabular-nums text-slate-900">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{caption}</div>
    </div>
  )
}

function Empty({ icon, text }) {
  return (
    <div className="flex items-center gap-3 px-5 py-8 text-sm text-slate-500">
      <Icon name={icon} className="h-5 w-5 text-slate-400" /> {text}
    </div>
  )
}

// ---------------------------------------------------------------- sections

function ReviewRow({ m, words, label, busy, onDecide }) {
  // Approving one meaning of an ambiguous word (3eish = rice) affects shoppers who meant the other.
  const w = words.words.find((x) => x.token === m.token)
  const alternatives = (w?.concepts ?? []).filter((c) => c !== m.concept)
  return (
    <li className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="rounded-md bg-slate-100 px-2 py-0.5 font-semibold text-slate-900" dir="auto">{m.token}</span>
          <Icon name="arrow" className="h-3.5 w-3.5 text-slate-400" />
          <span className="font-semibold text-slate-900">{label(m.concept)}</span>
        </div>
        <div className="mt-1.5 text-xs text-slate-500">
          {m.count} shopper confirmations · first seen {fmtDate(m.first_seen)} · from{' '}
          {m.examples.map((e, i) => (
            <span key={e} dir="auto">
              {i > 0 && ', '}“{e}”
            </span>
          ))}
        </div>
        {alternatives.length > 0 && (
          <div className="mt-1.5 flex items-center gap-1.5 text-xs text-amber-700">
            <Icon name="alert" className="h-3.5 w-3.5 shrink-0" />
            Also used for {alternatives.map(label).join(' or ')}. Approving shows only {label(m.concept)}.
          </div>
        )}
      </div>
      <div className="flex shrink-0 gap-2">
        <Button variant="secondary" size="sm" disabled={busy} onClick={() => onDecide(m.id, 'remove')}>
          Dismiss
        </Button>
        <Button variant="primary" size="sm" disabled={busy} onClick={() => onDecide(m.id, 'approve')}>
          <Icon name="check" className="h-3.5 w-3.5" /> Approve
        </Button>
      </div>
    </li>
  )
}

// Two series (typical vs ours) on one shared 0-max % scale, direct-labelled, with a legend.
function QualityChart({ overall }) {
  const metrics = [
    { label: 'Wrong product shown with no warning', typical: overall.fuzzy.silent_wrong, ours: overall.ours.silent_wrong },
    { label: 'No results for items in stock', typical: overall.fuzzy.zero, ours: overall.ours.zero },
  ]
  const max = Math.max(...metrics.flatMap((m) => [m.typical, m.ours]), 1)
  const bar = (value, color, who, metric) => (
    <div className="grid grid-cols-[4.5rem_1fr_3rem] items-center gap-2" title={`${who}: ${value}% (${metric})`}>
      <span className="text-xs text-slate-500">{who}</span>
      <span className="h-2 rounded-full bg-slate-100">
        <span className="block h-full rounded-full" style={{ width: `${(100 * value) / max}%`, background: color }} />
      </span>
      <span className="text-right text-xs font-medium tabular-nums text-slate-700">{value}%</span>
    </div>
  )
  return (
    <div className="space-y-5 px-5 py-4">
      <div className="flex gap-4 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SERIES_TYPICAL }} /> Typical search
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SERIES_OURS }} /> Our search
        </span>
      </div>
      {metrics.map((m) => (
        <div key={m.label} className="space-y-2">
          <div className="text-sm font-medium text-slate-800">{m.label}</div>
          {bar(m.typical, SERIES_TYPICAL, 'Typical', m.label)}
          {bar(m.ours, SERIES_OURS, 'Ours', m.label)}
        </div>
      ))}
      <p className="text-xs text-slate-400">Lower is better.</p>
    </div>
  )
}

// Single series: one hue, value and share written beside each bar.
function MissedBars({ rows, total }) {
  const max = Math.max(...rows.map((r) => r.zero_result_searches))
  return (
    <ol className="px-5 py-3">
      {rows.map((r, i) => (
        <li
          key={r.token}
          className="grid grid-cols-[1rem_4.5rem_1fr_3.75rem] items-center gap-2 rounded-lg px-1 py-2 hover:bg-slate-50 sm:grid-cols-[1.5rem_7rem_1fr_6.5rem] sm:gap-3"
          title={`“${r.token}”: ${r.zero_result_searches} of ${r.searches} searches found nothing`}
        >
          <span className="text-xs tabular-nums text-slate-400">{i + 1}</span>
          <span className="truncate text-sm font-medium text-slate-900" dir="auto">{r.token}</span>
          <span className="h-2 rounded-full bg-slate-100">
            <span className="block h-full rounded-full" style={{ width: `${(100 * r.zero_result_searches) / max}%`, background: SERIES_OURS }} />
          </span>
          <span className="text-right text-sm tabular-nums text-slate-700">
            {r.zero_result_searches}
            <span className="ml-1.5 text-xs text-slate-400">{Math.round((100 * r.zero_result_searches) / total)}%</span>
          </span>
        </li>
      ))}
    </ol>
  )
}

function Activity({ log, approved, label, busy, onUndo }) {
  const [all, setAll] = useState(false)
  if (log.length === 0) return <Empty icon="clock" text="No changes yet." />
  return (
    <div className="px-5 py-4">
      <ol className="relative space-y-4 border-l border-slate-200 pl-4">
        {(all ? log : log.slice(0, ACTIVITY_PREVIEW)).map((c) => (
          <li key={c.id} className="relative">
            <span className={`absolute -left-5.25 top-1.5 h-2.5 w-2.5 rounded-full ring-4 ring-white ${ACTIVITY[c.action]?.dot ?? 'bg-slate-400'}`} />
            <div className="text-sm text-slate-800">
              <span className="font-medium">{ACTIVITY[c.action]?.text ?? c.action}</span>{' '}
              <span className="font-semibold" dir="auto">{c.token}</span>
              <span className="text-slate-400"> → </span>
              {label(c.concept)}
            </div>
            <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
              {c.actor === 'store' ? 'By you' : 'Automatic, after shopper clicks'} · {fmtDate(c.ts)}
              {c.action === 'approved' && approved.some((m) => m.id === c.mapping_id) && (
                <button
                  disabled={busy === c.mapping_id}
                  onClick={() => onUndo(c.mapping_id)}
                  className="font-medium text-slate-600 underline underline-offset-2 hover:text-slate-900"
                >
                  Undo
                </button>
              )}
            </div>
          </li>
        ))}
      </ol>
      {log.length > ACTIVITY_PREVIEW && (
        <button onClick={() => setAll((s) => !s)} className="mt-4 text-xs font-medium text-slate-600 hover:text-slate-900">
          {all ? 'Show less' : `View all ${log.length}`}
        </button>
      )}
    </div>
  )
}

function WordTable({ words, label }) {
  const [tab, setTab] = useState('all')
  const shown = words.filter(TABS.find((t) => t.id === tab).test)
  return (
    <Panel
      title="Word insights"
      subtitle="Every word search wasn't fully sure about."
      right={
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                tab === t.id ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              {t.label} <span className="text-slate-400">{words.filter(t.test).length}</span>
            </button>
          ))}
        </div>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs text-slate-500">
              <th className="px-5 py-2.5 font-medium">Word</th>
              <th className="px-5 py-2.5 font-medium">Read as</th>
              <th className="px-5 py-2.5 text-right font-medium">Searches</th>
              <th className="px-5 py-2.5 text-right font-medium">No results</th>
              <th className="px-5 py-2.5 text-right font-medium">Complaints</th>
              <th className="px-5 py-2.5 font-medium">Learning</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {shown.map((w) => (
              <tr key={w.token} className="hover:bg-slate-50/70">
                <td className="px-5 py-3">
                  <div className="font-medium text-slate-900" dir="auto">{w.token}</div>
                  {w.language !== 'unknown' && <div className="text-xs text-slate-400">{languageLabel(w.language)}</div>}
                </td>
                <td className="px-5 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <ConfidencePill confidence={w.confidence} />
                    <span className="text-slate-600">
                      {w.concepts.length ? (
                        w.concepts.map(label).join(' or ')
                      ) : w.keyword ? (
                        `“${w.keyword}”`
                      ) : (
                        <span className="text-slate-400">not recognised</span>
                      )}
                    </span>
                  </div>
                </td>
                <td className="px-5 py-3 text-right tabular-nums text-slate-700">{w.searches}</td>
                <td className={`px-5 py-3 text-right tabular-nums ${w.zero_result_searches ? 'font-medium text-rose-700' : 'text-slate-400'}`}>
                  {w.zero_result_searches}
                </td>
                <td className={`px-5 py-3 text-right tabular-nums ${w.corrections ? 'font-medium text-amber-700' : 'text-slate-400'}`}>
                  {w.corrections}
                </td>
                <td className="px-5 py-3">
                  <Learning w={w} label={label} />
                </td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-slate-400">Nothing here.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

function Learning({ w, label }) {
  const best = [...w.mappings].sort((a, b) => b.count - a.count)[0]
  if (!best) return <span className="text-xs text-slate-400">No clicks yet</span>
  if (best.status === 'collecting')
    return (
      <div className="w-36">
        <div className="text-xs text-slate-500">
          {best.count}/{best.needed} clicks · {label(best.concept)}
        </div>
        <div className="mt-1 h-1.5 rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-slate-400" style={{ width: `${(100 * best.count) / best.needed}%` }} />
        </div>
      </div>
    )
  const pill = {
    proposed: ['To review', 'bg-amber-50 text-amber-800 ring-amber-200'],
    approved: ['Live', 'bg-emerald-50 text-emerald-800 ring-emerald-200'],
    removed: ['Dismissed', 'bg-slate-100 text-slate-600 ring-slate-200'],
  }[best.status]
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-600">
      <Pill className={pill[1]}>{pill[0]}</Pill> {label(best.concept)}
    </span>
  )
}
