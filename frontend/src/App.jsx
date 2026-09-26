import { useEffect, useState } from 'react'
import { api } from './api.js'
import LandingPage from './LandingPage.jsx'
import SearchPage from './SearchPage.jsx'
import StorePage from './StorePage.jsx'
import { Icon } from './ui.jsx'

// Three screens: "/" (choose who you are), "/shop" (customer), "/store" (manager).
// Plain links + pathname instead of a router dependency.
function currentPage() {
  const path = window.location.pathname
  if (path.startsWith('/store')) return 'store'
  if (path.startsWith('/shop')) return 'shop'
  return 'landing'
}

// Who can go where:
//   customer -> the customer page, plus a "Store manager sign-in" link that only reaches the
//               password screen (the server refuses dashboard data without a manager session)
//   manager  -> both: a switch between Dashboard and Customer view
// "Manager" comes from the server's session check, so a customer can't unlock the switch.
export default function App() {
  const page = currentPage()
  const [isManager, setIsManager] = useState(false)
  useEffect(() => {
    api
      .me()
      .then((r) => setIsManager(r.manager))
      .catch(() => setIsManager(false))
  }, [])

  const width = page === 'store' ? 'max-w-7xl' : 'max-w-6xl' // dashboard gets more room; header matches
  const tab = (href, label, icon, active) => (
    <a
      href={href}
      className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
        active ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200' : 'text-slate-600 hover:text-slate-900'
      }`}
    >
      <Icon name={icon} className="h-4 w-4" />
      {label}
    </a>
  )

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 backdrop-blur">
        <div className={`mx-auto flex items-center justify-between gap-4 px-4 py-3 sm:px-6 ${width}`}>
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-700 text-white shadow-sm">
              <Icon name="search" className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <div className="font-semibold tracking-tight">What You Meant</div>
              <div className="hidden text-xs text-slate-500 sm:block">Search that shows how it read you</div>
            </div>
          </div>
          {page !== 'landing' &&
            (isManager ? (
              <nav className="flex gap-1 rounded-xl bg-slate-100 p-1">
                {tab('/store', 'Dashboard', 'store', page === 'store')}
                {tab('/shop', 'Customer view', 'search', page === 'shop')}
              </nav>
            ) : page === 'shop' ? (
              // Leads only to the password screen; the dashboard's data is locked on the server.
              <a
                href="/store"
                className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-slate-200 transition-colors hover:bg-slate-50 hover:text-slate-900"
              >
                <Icon name="store" className="h-4 w-4" />
                Store manager sign-in
              </a>
            ) : (
              <span className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-600">
                <Icon name="store" className="h-4 w-4" />
                Store manager
              </span>
            ))}
        </div>
      </header>

      {page === 'shop' && isManager && (
        <div className="border-b border-sky-100 bg-sky-50">
          <div className={`mx-auto flex items-center gap-2 px-4 py-2 text-sm text-sky-900 sm:px-6 ${width}`}>
            <Icon name="info" className="h-4 w-4 shrink-0" />
            You're signed in as the store manager, viewing what customers see.
          </div>
        </div>
      )}

      <main className={`mx-auto px-4 py-8 sm:px-6 ${width}`}>
        {page === 'store' ? (
          <StorePage onAuthChange={setIsManager} />
        ) : page === 'shop' ? (
          <SearchPage />
        ) : (
          <LandingPage />
        )}
      </main>
      <footer className={`mx-auto px-4 pb-10 text-xs text-slate-400 sm:px-6 ${width}`}>
        Runs fully offline · no LLM · every guess is shown, never applied silently
      </footer>
    </div>
  )
}
