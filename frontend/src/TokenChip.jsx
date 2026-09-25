import { useState } from 'react'

export const CONFIDENCE_STYLE = {
  sure: { dot: '🟢', chip: 'bg-emerald-50 border-emerald-300 text-emerald-900', label: 'sure' },
  guessed: { dot: '🟡', chip: 'bg-amber-50 border-amber-300 text-amber-900', label: 'guessed' },
  unknown: { dot: '🔴', chip: 'bg-red-50 border-red-300 text-red-900', label: 'unknown' },
}

function meaning(t) {
  if (t.role === 'quantity') return 'quantity'
  if (t.role === 'filler') return 'ignored (connecting word)'
  if (t.role === 'keyword') return `product word "${t.keyword}"`
  if (t.concept_labels.length) return t.concept_labels.join(' or ')
  return 'not recognised'
}

// One token of the query. Hover (desktop) or tap (mobile) to see the full explanation.
export default function TokenChip({ token: t }) {
  const [open, setOpen] = useState(false)
  const quiet = t.role === 'filler' || t.role === 'quantity'
  const style = quiet
    ? 'bg-stone-100 border-stone-200 text-stone-500'
    : CONFIDENCE_STYLE[t.confidence].chip

  return (
    <span className="relative inline-block" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`border rounded-lg px-2.5 py-1 text-sm text-left ${style}`}
      >
        {!quiet && <span className="mr-1">{CONFIDENCE_STYLE[t.confidence].dot}</span>}
        <span className="font-medium">{t.original}</span>
        {!quiet && <span className="opacity-70"> → {meaning(t)}</span>}
      </button>

      {open && (
        <div className="absolute z-20 left-0 top-full mt-1 w-80 rounded-lg border border-stone-200 bg-white p-3 shadow-lg text-sm">
          <Row k="You typed" v={t.original} />
          <Row k="Normalized" v={t.normalized} />
          <Row k="Meaning" v={meaning(t)} />
          <Row k="Language" v={`${t.language_label}${t.language_reason ? ` (${t.language_reason})` : ''}`} />
          <Row
            k="Confidence"
            v={`${CONFIDENCE_STYLE[t.confidence].label}${t.score != null ? `, ${t.score}% similar to "${t.similar_to}"` : ''}`}
          />
          <Row k="Why" v={t.why} />
          {t.steps.length > 0 && (
            <div className="mt-2 border-t border-stone-100 pt-2">
              <div className="text-xs font-medium text-stone-500 mb-1">Steps</div>
              <ol className="list-decimal list-inside text-xs text-stone-600 space-y-0.5">
                {t.steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}
          {t.notes.length > 0 && (
            <div className="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-900">{t.notes.join(' ')}</div>
          )}
        </div>
      )}
    </span>
  )
}

function Row({ k, v }) {
  return (
    <div className="flex gap-2 py-0.5">
      <div className="w-24 shrink-0 text-stone-500">{k}</div>
      <div className="break-words min-w-0">{v}</div>
    </div>
  )
}
