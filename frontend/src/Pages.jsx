import React, { useEffect, useMemo, useState } from 'react'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, BarChart, Bar } from 'recharts'
import { api, studentId, setStudentId } from './api'
import { Card, Chip, Btn, Banner, Rich, STATE_TONE } from './ui'

// ---------------------------------------------------------------- landing
export function Landing({ goto, startDemo, health }) {
  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-indigo-700 via-indigo-600 to-violet-600 text-white p-8 sm:p-12">
        <div className="text-sm font-semibold opacity-80 mb-2">Maharashtra SSC - Std 9 &amp; 10 Algebra</div>
        <h1 className="text-3xl sm:text-5xl font-extrabold leading-tight">We don't just detect wrong answers.<br />We detect the thinking error behind them.</h1>
        <p className="mt-4 max-w-2xl opacity-90">Re:Learn reads your working step by step, names the misconception with evidence, teaches that exact idea, then checks - with a new question and a transfer question - whether it is truly fixed.</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button onClick={startDemo} className="px-5 py-3 rounded-xl bg-white text-indigo-700 font-bold hover:bg-indigo-50">Run the demo: 3(x + 2) = 15</button>
          <button onClick={() => goto('topics')} className="px-5 py-3 rounded-xl bg-indigo-500/40 border border-white/40 font-semibold hover:bg-indigo-500/60">Choose a topic</button>
        </div>
      </div>
      <div className="grid md:grid-cols-4 gap-4">
        {[['1', 'Diagnose', 'Rule checks on every step + dataset matching. It abstains when evidence is thin.'],
          ['2', 'Teach', 'Intervention chosen by the misconception, not the question.'],
          ['3', 'Reassess + Transfer', 'A new item, then a different form. One right answer is not mastery.'],
          ['4', 'Learner model', 'Your Misconception Fingerprint tracks New / Improving / Persistent / Resolved.']].map(([n, t, d]) => (
          <Card key={n}><div className="text-indigo-600 font-extrabold text-2xl">{n}</div><div className="font-bold">{t}</div><p className="text-sm text-slate-600 mt-1">{d}</p></Card>))}
      </div>
      <p className="text-xs text-slate-500">Backend: {health ? `online - ${health.questions} questions, ${health.misconceptions} misconceptions, Ollama ${health.ollama ? 'on' : 'off (dataset text used)'}` : 'not reachable - start uvicorn on port 8000'}</p>
    </div>
  )
}

// ---------------------------------------------------------------- topic selection
export function Topics({ onPick }) {
  const [meta, setMeta] = useState(null); const [std, setStd] = useState(10); const [chapter, setChapter] = useState('')
  const [diff, setDiff] = useState(''); const [qs, setQs] = useState([]); const [err, setErr] = useState('')
  useEffect(() => { api.meta().then(setMeta).catch(() => setErr('Backend not reachable.')) }, [])
  useEffect(() => { if (meta) { const t = meta.topics.find((t) => t.standard === std); setChapter((c) => (meta.topics.some((x) => x.chapter === c && x.standard === std) ? c : t?.chapter || '')) } }, [std, meta])
  useEffect(() => { if (chapter) api.questions({ standard: std, chapter, difficulty: diff }).then(setQs).catch(() => {}) }, [std, chapter, diff])
  if (err) return <Banner tone="red" title="Error">{err}</Banner>
  if (!meta) return <p>Loading...</p>
  return (
    <div className="space-y-5">
      <Card className="space-y-4">
        <div><div className="text-xs font-semibold text-slate-500 mb-1">STANDARD</div>
          <div className="flex gap-2">{[9, 10].map((s) => <Btn key={s} variant={std === s ? 'dark' : 'ghost'} onClick={() => setStd(s)}>Standard {s}</Btn>)}</div></div>
        <div><div className="text-xs font-semibold text-slate-500 mb-1">TOPIC</div>
          <div className="flex flex-wrap gap-2">{meta.topics.filter((t) => t.standard === std).map((t) => <Btn key={t.chapter} variant={chapter === t.chapter ? 'dark' : 'ghost'} onClick={() => setChapter(t.chapter)}>{t.chapter}</Btn>)}</div></div>
        <div><div className="text-xs font-semibold text-slate-500 mb-1">DIFFICULTY</div>
          <div className="flex gap-2">{['', ...meta.difficulties].map((d) => <Btn key={d} variant={diff === d ? 'dark' : 'ghost'} onClick={() => setDiff(d)}>{d || 'Any'}</Btn>)}</div></div>
      </Card>
      <div className="grid sm:grid-cols-2 gap-3">
        {qs.map((q) => (
          <button key={q.question_id} onClick={() => onPick(q)} className="text-left rounded-2xl bg-white border border-slate-200 p-4 hover:border-indigo-400 hover:shadow transition">
            <div className="flex gap-2 mb-2"><Chip tone="amber">{q.difficulty}</Chip><Chip>{q.topic}</Chip></div>
            <div><Rich>{q.question}</Rich></div>
          </button>))}
        {qs.length === 0 && <p className="text-slate-500">No questions for this selection.</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- fingerprint + progress
export function Fingerprint() {
  const [sid, setSid] = useState(studentId()); const [data, setData] = useState(null); const [err, setErr] = useState('')
  const load = () => api.learner(sid).then((d) => { setData(d); setErr('') }).catch(() => setErr('Backend not reachable.'))
  useEffect(() => { load() }, [])
  if (err) return <Banner tone="red" title="Error">{err}</Banner>
  if (!data) return <p>Loading...</p>
  const radar = Object.entries(data.fingerprint).map(([k, v]) => ({ axis: k, Active: v.New + v.Persistent + v.Improving, Resolved: v.Resolved }))
  const prog = data.timeline.map((t, i) => ({ n: i + 1, 'Misconceptions seen': t.seen_so_far, Resolved: t.resolved_so_far }))
  return (
    <div className="space-y-5">
      <Card className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-semibold">Student ID</span>
        <input value={sid} onChange={(e) => setSid(e.target.value)} className="border rounded-lg px-3 py-1.5 text-sm" />
        <Btn variant="ghost" onClick={() => { setStudentId(sid); load() }}>Load</Btn>
        <div className="ml-auto flex gap-2"><Chip tone="slate">seen {data.summary.seen}</Chip><Chip tone="blue">improving {data.summary.improving}</Chip><Chip tone="red">persistent {data.summary.persistent}</Chip><Chip tone="green">resolved {data.summary.resolved}</Chip></div>
      </Card>
      <div className="grid lg:grid-cols-2 gap-5">
        <Card><div className="font-bold mb-2">Misconception Fingerprint</div>
          <div style={{ height: 300 }}><ResponsiveContainer><RadarChart data={radar}><PolarGrid /><PolarAngleAxis dataKey="axis" tick={{ fontSize: 11 }} />
            <Radar name="Active" dataKey="Active" stroke="#e11d48" fill="#e11d48" fillOpacity={0.35} /><Radar name="Resolved" dataKey="Resolved" stroke="#059669" fill="#059669" fillOpacity={0.3} /><Legend /><Tooltip /></RadarChart></ResponsiveContainer></div></Card>
        <Card><div className="font-bold mb-2">Progress over time</div>
          {prog.length ? <div style={{ height: 300 }}><ResponsiveContainer><LineChart data={prog}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="n" label={{ value: 'learning events', position: 'insideBottom', offset: -2, fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Legend />
            <Line type="monotone" dataKey="Misconceptions seen" stroke="#6366f1" strokeWidth={2} /><Line type="monotone" dataKey="Resolved" stroke="#059669" strokeWidth={2} /></LineChart></ResponsiveContainer></div> : <p className="text-sm text-slate-500">No activity yet - solve a question first.</p>}</Card>
      </div>
      <Card><div className="font-bold mb-3">Your misconceptions</div>
        {data.misconceptions.length === 0 && <p className="text-sm text-slate-500">None recorded yet.</p>}
        <div className="space-y-2">{data.misconceptions.map((m) => (
          <div key={m.misconception_id} className="flex flex-wrap items-center gap-2 rounded-xl border p-3">
            <Chip tone={STATE_TONE[m.state]}>{m.state}</Chip><div className="font-medium">{m.name}</div>
            <span className="text-xs text-slate-500">{m.type} - {m.topic}</span><span className="ml-auto text-xs text-slate-500">{m.status_label} - {m.attempts} attempt{m.attempts > 1 ? 's' : ''}</span>
          </div>))}</div></Card>
    </div>
  )
}

// ---------------------------------------------------------------- misconception map
const COLS = [['topic', 'Topic'], ['concept', 'Concept'], ['misconception', 'Misconception'], ['intervention', 'Intervention'], ['resolution', 'Resolution']]
export function MapPage() {
  const [g, setG] = useState(null); const [topic, setTopic] = useState(null); const [mine, setMine] = useState({}); const [hover, setHover] = useState(null)
  useEffect(() => { api.map().then(setG).catch(() => {}); api.learner(studentId()).then((d) => setMine(Object.fromEntries(d.misconceptions.map((m) => [m.misconception_id, m.state])))).catch(() => {}) }, [])
  const topics = useMemo(() => (g ? g.nodes.filter((n) => n.kind === 'topic') : []), [g])
  useEffect(() => { if (topics.length && !topic) setTopic(topics[0].id) }, [topics])
  if (!g) return <p>Loading...</p>
  const keep = new Set([topic]); g.links.forEach((l) => { if (l.source === topic) keep.add(l.target) })
  g.links.forEach((l) => { if (keep.has(l.source)) keep.add(l.target) }); g.links.forEach((l) => { if (keep.has(l.source)) keep.add(l.target) })
  const nodes = g.nodes.filter((n) => keep.has(n.id)); const links = g.links.filter((l) => keep.has(l.source) && keep.has(l.target))
  const W = 1100, rowH = 34, byKind = Object.fromEntries(COLS.map(([k]) => [k, nodes.filter((n) => n.kind === k)]))
  const H = Math.max(260, Math.max(...Object.values(byKind).map((a) => a.length)) * rowH + 60)
  const pos = {}; COLS.forEach(([k], ci) => byKind[k].forEach((n, i) => { pos[n.id] = [60 + ci * 245, 50 + i * ((H - 70) / Math.max(1, byKind[k].length)) + 10] }))
  const color = (n) => { const id = n.id.slice(2); const st = mine[id]; if (n.kind === 'misconception') return st ? ({ New: '#f59e0b', Improving: '#0ea5e9', Persistent: '#e11d48', Resolved: '#059669' }[st]) : '#cbd5e1'; return { topic: '#4f46e5', concept: '#7c3aed', intervention: '#0891b2', resolution: '#059669' }[n.kind] }
  const active = hover && new Set(links.filter((l) => [l.source, l.target].includes(hover)).flatMap((l) => [l.source, l.target]))
  return (
    <div className="space-y-4">
      <Card><div className="flex flex-wrap gap-2">{topics.map((t) => <Btn key={t.id} variant={topic === t.id ? 'dark' : 'ghost'} onClick={() => setTopic(t.id)}>{t.label}</Btn>)}</div>
        <p className="text-xs text-slate-500 mt-2">Topic - Concept - Misconception - Intervention - Resolution. Misconceptions you have met are coloured by status; grey = not met yet. Hover to trace a path.</p></Card>
      <Card className="overflow-x-auto"><svg width={W} height={H} className="min-w-[1000px]">
        {COLS.map(([k, label], ci) => <text key={k} x={60 + ci * 245} y={22} className="fill-slate-400" fontSize="12" fontWeight="700">{label.toUpperCase()}</text>)}
        {links.map((l, i) => { const a = pos[l.source], b = pos[l.target]; if (!a || !b) return null; const on = !active || (active.has(l.source) && active.has(l.target))
          return <path key={i} d={`M${a[0] + 150},${a[1]} C${a[0] + 200},${a[1]} ${b[0] - 50},${b[1]} ${b[0]},${b[1]}`} stroke="#94a3b8" strokeWidth="1.2" fill="none" opacity={on ? 0.8 : 0.08} /> })}
        {nodes.map((n) => { const p = pos[n.id]; if (!p) return null; const on = !active || active.has(n.id)
          return <g key={n.id} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} opacity={on ? 1 : 0.25}>
            <rect x={p[0]} y={p[1] - 12} width={150} height={24} rx={8} fill={color(n)} /><title>{n.label}</title>
            <text x={p[0] + 8} y={p[1] + 4} fontSize="10.5" fill="white" fontWeight="600">{n.label.length > 24 ? n.label.slice(0, 23) + '...' : n.label}</text></g> })}
      </svg></Card>
    </div>
  )
}

// ---------------------------------------------------------------- evaluation + teacher
export function Evaluation() {
  const [ev, setEv] = useState(null); const [t, setT] = useState(null); const [err, setErr] = useState('')
  useEffect(() => { api.evaluation().then(setEv).catch(() => setErr('Run "python -m app.evaluate" in backend/ to generate the report.')); api.teacher().then(setT).catch(() => {}) }, [])
  const A = ev?.A_ml_on_simulated_attempts, B = ev?.B_full_engine_on_typed_cases, C = ev?.C_unseen_misconceptions
  const Row = ({ k, v }) => <div className="flex justify-between text-sm border-b py-1.5"><span className="text-slate-600">{k}</span><b>{String(v)}</b></div>
  return (
    <div className="space-y-5">
      <Banner tone="amber" title="Read this before quoting any number">Every score here comes from SIMULATED data (supplied CSVs) or developer-written typed cases. No real student results exist yet.</Banner>
      {err && <Banner tone="red" title="No report">{err}</Banner>}
      {ev && <div className="grid lg:grid-cols-3 gap-4">
        <Card><div className="font-bold mb-1">A. ML on supplied simulated attempts</div><p className="text-xs text-slate-500 mb-2">{ev.dataset_caveat}</p>
          {Object.entries(A).map(([name, r]) => <div key={name} className="mb-3"><div className="text-xs font-semibold text-indigo-600">{name}</div>
            <Row k="misconception accuracy (wrong attempts)" v={r.misconception_accuracy_on_wrong_attempts} /><Row k="macro F1" v={r.misconception_metrics_on_wrong_attempts.macro_f1} /><Row k="detect wrong vs not: F1" v={r.detect_f1} /><div className="text-[11px] text-slate-400">{r.chance_level_note}</div></div>)}</Card>
        <Card><div className="font-bold mb-1">B. Full engine on typed cases</div><p className="text-xs text-slate-500 mb-2">{B.note} (n={B.n_cases})</p>
          <Row k="misconception accuracy" v={B.misconception_cases.accuracy} /><Row k="macro precision" v={B.misconception_cases.macro_precision} /><Row k="macro recall" v={B.misconception_cases.macro_recall} /><Row k="macro F1" v={B.misconception_cases.macro_f1} />
          <Row k="false alarms on correct working" v={`${B.false_alarm_on_correct_working.false_diagnoses} / ${B.false_alarm_on_correct_working.n}`} />
          <Row k="correct abstentions" v={`${B.abstention_on_insufficient_evidence.correctly_abstained} / ${B.abstention_on_insufficient_evidence.n}`} /></Card>
        <Card><div className="font-bold mb-1">C. Unseen misconceptions (ML)</div><p className="text-xs text-slate-500 mb-2">{C.note}</p>
          <Row k="attempts tested" v={C.unseen_misconception_attempts} /><Row k="wrongly forced a label" v={C.forced_wrong_label} /><Row k="abstained / none" v={C.abstained_or_none} /><Row k="abstention rate" v={C.abstention_rate} /></Card>
      </div>}
      {t && <Card><div className="font-bold mb-1">Teacher view - most common misconceptions on this server</div><p className="text-xs text-slate-500 mb-2">{t.students} student(s)</p>
        {t.misconceptions.length ? <div style={{ height: 260 }}><ResponsiveContainer><BarChart data={t.misconceptions} layout="vertical" margin={{ left: 150 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }} /><Tooltip /><Legend />
          <Bar dataKey="total" fill="#6366f1" name="Occurrences" /><Bar dataKey="resolved" fill="#059669" name="Resolved" /></BarChart></ResponsiveContainer></div> : <p className="text-sm text-slate-500">No data yet - run the demo.</p>}</Card>}
    </div>
  )
}
