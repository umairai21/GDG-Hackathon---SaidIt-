import { CONFIDENCE, ConfidencePill, Icon } from './ui.jsx'

export const isQuiet = (t) => t.role === 'filler' || t.role === 'quantity'

export function meaning(t) {
  if (t.role === 'quantity') return 'quantity'
  if (t.role === 'filler') return 'ignored'
  if (t.role === 'keyword') return `“${t.keyword}”`
  if (t.concept_labels.length) return t.concept_labels.join(' or ')
  return 'not recognised'
}

// One word of the query. Click to see how it was read in the detail panel below.
export default function TokenChip({ token: t, selected, onSelect }) {
  if (isQuiet(t)) {
    return (
      <span className="inline-flex flex-col rounded-xl px-3 py-2 text-left ring-1 ring-inset ring-slate-200 bg-slate-50">
        <span className="font-medium text-slate-500" dir="auto">{t.original}</span>
        <span className="text-xs text-slate-400">{meaning(t)}</span>
      </span>
    )
  }
  const c = CONFIDENCE[t.confidence]
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`inline-flex flex-col rounded-xl px-3 py-2 text-left ring-1 ring-inset transition ${
        selected ? c.selected : c.chip
      }`}
    >
      <span className="flex items-center gap-1.5 font-semibold text-slate-900">
        <span className={`h-2 w-2 rounded-full ${c.dot}`} />
        <span dir="auto">{t.original}</span>
      </span>
      <span className={`text-xs ${c.text}`}>{meaning(t)}</span>
    </button>
  )
}

// The "why" for one word: typed -> normalized -> meaning, then language, rule and steps.
export function TokenDetail({ token: t }) {
  const c = CONFIDENCE[t.confidence]
  return (
    <div className="fade-in rounded-xl border border-slate-200 bg-slate-50/60 p-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Stage label="You typed" value={t.original} />
        <Icon name="arrow" className="h-4 w-4 text-slate-400" />
        <Stage label="Normalized" value={t.normalized} />
        <Icon name="arrow" className="h-4 w-4 text-slate-400" />
        <Stage label="Meaning" value={meaning(t)} strong />
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <Fact label="Confidence">
          <div className="flex items-center gap-2">
            <ConfidencePill confidence={t.confidence} />
            {t.score != null && <span className="text-slate-600">{t.score}% similar</span>}
          </div>
          {t.score != null && (
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div className={`h-full ${c.bar}`} style={{ width: `${t.score}%` }} />
            </div>
          )}
          {t.similar_to && <div className="mt-1 text-xs text-slate-500">closest known spelling: “{t.similar_to}”</div>}
        </Fact>
        <Fact label="Language">
          <div className="font-medium">{t.language_label}</div>
          <div className="text-xs text-slate-500">{t.language_reason}</div>
        </Fact>
        <Fact label="Rule used">
          <div className="font-medium">{t.why}</div>
          <code className="text-xs text-slate-400">{t.method}</code>
        </Fact>
      </dl>

      {t.steps.length > 0 && (
        <details className="group mt-3 text-sm">
          <summary className="cursor-pointer select-none text-slate-600 hover:text-slate-900">
            How we got there ({t.steps.length} {t.steps.length === 1 ? 'step' : 'steps'})
          </summary>
          <ol className="mt-2 space-y-1 border-l-2 border-slate-200 pl-4 text-slate-600">
            {t.steps.map((s, i) => (
              <li key={i} dir="auto">{s}</li>
            ))}
          </ol>
        </details>
      )}

      {t.notes.length > 0 && (
        <div className="mt-3 flex gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-inset ring-amber-200">
          <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{t.notes.join(' ')}</span>
        </div>
      )}
    </div>
  )
}

function Stage({ label, value, strong }) {
  return (
    <div className={`rounded-lg px-3 py-1.5 ring-1 ring-inset ${strong ? 'bg-white ring-slate-300' : 'bg-white ring-slate-200'}`}>
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className={strong ? 'font-semibold' : 'font-medium text-slate-700'} dir="auto">{value}</div>
    </div>
  )
}

function Fact({ label, children }) {
  return (
    <div>
      <dt className="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
