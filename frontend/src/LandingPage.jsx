import { Icon } from './ui.jsx'

// Entry point: pick who you are. No sign-in; it's a demo with two audiences.
export default function LandingPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-4xl flex-col items-center justify-center py-8 text-center">
      <div className="grid h-14 w-14 place-items-center rounded-2xl bg-emerald-700 text-white shadow-md">
        <Icon name="search" className="h-7 w-7" />
      </div>
      <h1 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">What You Meant</h1>
      <p className="mt-3 max-w-xl text-lg text-slate-600">
        Grocery search that understands how people in the UAE really type, and never changes your words silently.
      </p>

      <div className="mt-10 grid w-full gap-4 sm:grid-cols-2">
        <Choice
          href="/shop"
          emoji="🛒"
          title="I'm a customer"
          text="Search for groceries in any language or spelling."
          accent="group-hover:border-emerald-500"
        />
        <Choice
          href="/store"
          emoji="🏪"
          title="I'm the store manager"
          text="Sign in to see what customers couldn't find, and approve what search learns."
          accent="group-hover:border-sky-500"
        />
      </div>

      <p className="mt-6 text-sm text-slate-400">Customers don't need to sign in. The store dashboard needs the manager password.</p>
    </div>
  )
}

function Choice({ href, emoji, title, text, accent }) {
  return (
    <a
      href={href}
      className={`group flex flex-col items-center rounded-3xl border-2 border-slate-200 bg-white p-8 shadow-sm transition hover:-translate-y-1 hover:shadow-lg ${accent}`}
    >
      <span className="grid h-20 w-20 place-items-center rounded-2xl bg-slate-100 text-5xl transition group-hover:scale-105">
        {emoji}
      </span>
      <span className="mt-5 text-xl font-semibold text-slate-900">{title}</span>
      <span className="mt-2 text-slate-500">{text}</span>
      <span className="mt-auto inline-flex items-center gap-2 pt-6 font-medium text-emerald-700">
        Continue <Icon name="arrow" className="h-4 w-4 transition group-hover:translate-x-1" />
      </span>
    </a>
  )
}
