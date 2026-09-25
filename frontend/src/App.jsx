import SearchPage from './SearchPage.jsx'
import StorePage from './StorePage.jsx'

// Two pages only, so plain links + pathname instead of a router dependency.
export default function App() {
  const isStore = window.location.pathname.startsWith('/store')
  const tab = (href, label, active) => (
    <a
      href={href}
      className={`px-3 py-1.5 rounded-md text-sm font-medium ${
        active ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-200'
      }`}
    >
      {label}
    </a>
  )
  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between gap-4">
          <div>
            <div className="font-semibold">What You Meant</div>
            <div className="text-xs text-stone-500">Search that shows how it read you. No silent corrections.</div>
          </div>
          <nav className="flex gap-1">
            {tab('/', 'Customer search', !isStore)}
            {tab('/store', 'Store dashboard', isStore)}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{isStore ? <StorePage /> : <SearchPage />}</main>
    </div>
  )
}
