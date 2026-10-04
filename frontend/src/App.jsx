import React, { useEffect, useState } from 'react'
import { api } from './api'
import Solve from './Solve'
import { Landing, Topics, Fingerprint, MapPage, Evaluation } from './Pages'

const NAV = [['home', 'Home'], ['topics', 'Practice'], ['fingerprint', 'My Fingerprint'], ['map', 'Misconception Map'], ['eval', 'Evaluation & Teacher']]

export default function App() {
  const [page, setPage] = useState('home'); const [pick, setPick] = useState(null); const [demo, setDemo] = useState(null)
  const [health, setHealth] = useState(null); const [k, setK] = useState(0)
  useEffect(() => { api.health().then(setHealth).catch(() => setHealth(null)) }, [])
  const goto = (p) => { if (p !== 'solve') { setPick(null); setDemo(null) } setPage(p) }
  const startDemo = async () => { const d = (await api.demos())[0]; setDemo(d); setPick(null); setK((n) => n + 1); setPage('solve') }
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 bg-white/90 backdrop-blur border-b">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
          <button onClick={() => goto('home')} className="font-extrabold text-indigo-700 text-lg">Re:Learn</button>
          <nav className="flex gap-1 overflow-x-auto">{NAV.map(([id, label]) => (
            <button key={id} onClick={() => goto(id)} className={`px-3 py-1.5 rounded-lg text-sm font-semibold whitespace-nowrap ${page === id ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`}>{label}</button>))}</nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        {page === 'home' && <Landing goto={goto} startDemo={startDemo} health={health} />}
        {page === 'topics' && <Topics onPick={(q) => { setPick(q); setK((n) => n + 1); setPage('solve') }} />}
        {page === 'solve' && <Solve key={k} pick={pick} demo={demo} goto={goto} />}
        {page === 'fingerprint' && <Fingerprint />}
        {page === 'map' && <MapPage />}
        {page === 'eval' && <Evaluation />}
      </main>
    </div>
  )
}
