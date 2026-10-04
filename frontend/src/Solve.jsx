import React, { useEffect, useState } from 'react'
import { api, studentId } from './api'
import { Card, Chip, Btn, Banner, Tex, Rich, DrawPad, STATE_TONE } from './ui'

function StepInput({ steps, setSteps, final, setFinal, disabled }) {
  const [mode, setMode] = useState('type')
  const [ocrMsg, setOcrMsg] = useState('')
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Btn variant={mode === 'type' ? 'dark' : 'ghost'} onClick={() => setMode('type')}>Type steps</Btn>
        <Btn variant={mode === 'draw' ? 'dark' : 'ghost'} onClick={() => setMode('draw')}>Draw / handwrite</Btn>
      </div>
      {mode === 'draw' && (
        <div>
          <DrawPad onExport={async (img) => { try { const r = await api.ocr(img); setOcrMsg(r.message || r.text) } catch { setOcrMsg('OCR service unreachable.') } }} />
          {ocrMsg && <p className="text-sm text-amber-700 mt-2">{ocrMsg}</p>}
        </div>
      )}
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-16 text-xs font-semibold text-slate-500">Step {i + 1}</span>
          <input disabled={disabled} value={s} onChange={(e) => setSteps(steps.map((v, j) => (j === i ? e.target.value : v)))}
            placeholder={i === 0 ? 'e.g. 3x + 6 = 15' : 'next line of working'}
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          {steps.length > 1 && !disabled && <button className="text-slate-400 hover:text-rose-500" onClick={() => setSteps(steps.filter((_, j) => j !== i))}>x</button>}
        </div>
      ))}
      {!disabled && <Btn variant="ghost" onClick={() => setSteps([...steps, ''])}>+ Add step</Btn>}
      <div className="flex items-center gap-2 pt-1">
        <span className="w-16 text-xs font-semibold text-indigo-600">Answer</span>
        <input disabled={disabled} value={final} onChange={(e) => setFinal(e.target.value)} placeholder="final answer, e.g. x = 3"
          className="flex-1 rounded-lg border-2 border-indigo-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </div>
    </div>
  )
}

function Diagnosis({ res }) {
  const d = res.diagnosis_result, dg = d.diagnosis
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-3">
        <Card className="!p-4"><div className="text-xs text-slate-500">Final answer</div>
          <div className="mt-1">{d.answer_correct === true ? <Chip tone="green">Correct</Chip> : d.answer_correct === false ? <Chip tone="red">Incorrect</Chip> : <Chip>Cannot judge</Chip>}</div></Card>
        <Card className="!p-4"><div className="text-xs text-slate-500">Reasoning</div>
          <div className="mt-1">{d.status === 'correct' ? <Chip tone="green">Sound</Chip> : dg || d.status === 'answer_correct_reasoning_flawed' ? <Chip tone="red">Flawed</Chip> : <Chip tone="amber">Not enough evidence</Chip>}</div></Card>
      </div>
      <Card>
        <div className="text-xs font-semibold text-slate-500 mb-2">YOUR WORKING</div>
        <div className="space-y-1">
          {d.steps.length === 0 && <div className="text-sm text-slate-400">No steps were entered.</div>}
          {d.steps.map((s) => (
            <div key={s.index} className={`flex items-center gap-3 rounded-lg px-3 py-2 ${s.flag === 'error' ? 'bg-rose-50 ring-2 ring-rose-300' : s.flag === 'unexplained' ? 'bg-amber-50 ring-2 ring-amber-300' : 'bg-slate-50'}`}>
              <span className="text-xs font-bold text-slate-400 w-12">Step {s.index}</span><Tex>{s.text}</Tex>
              {s.flag === 'error' && <Chip tone="red">error here</Chip>}{s.flag === 'unexplained' && <Chip tone="amber">doesn't follow</Chip>}
            </div>))}
        </div>
      </Card>
      {dg && (
        <Banner tone="red" title={`Misconception detected: ${dg.misconception_name}`}>
          <div className="flex gap-2 flex-wrap mb-2"><Chip tone="violet">{dg.misconception_type || 'Misconception'}</Chip>
            <Chip tone="slate">confidence {Math_pct(dg.confidence)}</Chip><Chip tone="slate">{dg.source.startsWith('rule') ? 'rule-based evidence' : 'dataset match (weaker)'}</Chip></div>
          <div className="font-semibold">Evidence</div><p className="mb-1"><Rich>{dg.evidence}</Rich></p>
          {dg.expected_step && <p className="text-xs">Expected: <Tex>{dg.expected_step}</Tex></p>}
        </Banner>)}
      {!dg && d.message && <Banner tone="amber" title={d.status === 'answer_correct_reasoning_flawed' ? 'Right answer, shaky reasoning' : 'Not enough evidence to diagnose'}>{d.message}</Banner>}
      {d.status === 'correct' && <Banner tone="green" title="Correct answer and sound reasoning">Nothing to fix here. Try the next question.</Banner>}
      {d.alternatives?.length > 0 && <p className="text-xs text-slate-500">Also considered: {d.alternatives.map((a) => `${a.misconception_name} (${Math_pct(a.confidence)})`).join('; ')}</p>}
    </div>
  )
}
const Math_pct = (c) => Math_round(c * 100) + '%'
const Math_round = (v) => Number(v.toFixed(0))

function StageCard({ title, tone, question, demo, onSubmit, busy, result }) {
  const [steps, setSteps] = useState(['']); const [final, setFinal] = useState('')
  return (
    <Card className="space-y-4">
      <div className="flex items-center gap-2"><Chip tone={tone}>{title}</Chip></div>
      <div className="text-lg"><Rich>{question}</Rich></div>
      <StepInput steps={steps} setSteps={setSteps} final={final} setFinal={setFinal} />
      <div className="flex gap-2">
        <Btn disabled={busy || !final.trim()} onClick={() => onSubmit(steps.filter((s) => s.trim()).join('\n'), final)}>{busy ? 'Checking...' : 'Submit'}</Btn>
        {demo && <Btn variant="ghost" onClick={() => { setSteps(demo.working.split('\n')); setFinal(demo.final_answer) }}>Autofill demo answer</Btn>}
      </div>
      {result && <Banner tone={result.passed ? 'green' : 'amber'} title={result.status_label}>{result.message}</Banner>}
    </Card>)
}

export default function Solve({ pick, demo, goto }) {
  const [q, setQ] = useState(pick || null)
  const [steps, setSteps] = useState(demo ? demo.working.split('\n') : [''])
  const [final, setFinal] = useState(demo ? demo.final_answer : '')
  const [res, setRes] = useState(null); const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState(null)          // intervention | reassessment | transfer | done
  const [stageRes, setStageRes] = useState(null); const [err, setErr] = useState('')
  const [status, setStatus] = useState(null)
  const iv = res?.intervention

  useEffect(() => { if (demo && !q) api.questions({}).then((all) => setQ(all.find((x) => x.question_id === demo.question_id))) }, [])
  if (!q) return <Card>No question selected. <button className="text-indigo-600 underline" onClick={() => goto('topics')}>Choose a topic</button></Card>

  const submit = async () => {
    setBusy(true); setErr('')
    try {
      const r = await api.submit({ student_id: studentId(), question_id: q.question_id, working: steps.filter((s) => s.trim()).join('\n'), final_answer: final })
      setRes(r); setStatus(r.status); setStage(r.next === 'intervention' ? 'intervention' : null)
    } catch (e) { setErr('Backend not reachable. Is uvicorn running on port 8000?') }
    setBusy(false)
  }
  const sendStage = async (kind, working, fin) => {
    setBusy(true)
    try {
      const r = await api.stage(res.session_id, kind, { working, final_answer: fin })
      setStageRes(r); setStatus(r.status)
      setStage(r.next === 'transfer' ? 'transfer' : r.next === 'retry_reassessment' ? 'reassessment' : r.next === 'retry_transfer' ? 'transfer' : r.next === 'reintervene' ? 'reintervene' : r.next === 'done' ? 'done' : stage)
    } catch (e) { setErr(String(e.message || e)) }
    setBusy(false)
  }
  const startReassess = async () => { await api.interventionDone(res.session_id); setStageRes(null); setStage('reassessment'); setStatus('intervention_completed') }

  const pipeline = ['Attempt', 'Diagnosis', 'Intervention', 'Reassessment', 'Transfer', 'Resolution']
  const at = !res ? 0 : stage === 'intervention' ? 2 : stage === 'reintervene' ? 2 : stage === 'reassessment' ? 3 : stage === 'transfer' ? 4 : stage === 'done' ? 5 : 1

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-1 text-xs font-semibold">
        {pipeline.map((p, i) => <span key={p} className={`px-3 py-1 rounded-full ${i < at ? 'bg-indigo-600 text-white' : i === at ? 'bg-indigo-100 text-indigo-800 ring-2 ring-indigo-400' : 'bg-slate-100 text-slate-400'}`}>{p}</span>)}
        {status && <span className="ml-auto"><Chip tone={status === 'resolved' ? 'green' : status === 'persistent' ? 'red' : status === 'improving' ? 'blue' : 'amber'}>{status.replace('_', ' ')}</Chip></span>}
      </div>
      <Card>
        <div className="flex gap-2 mb-2"><Chip tone="blue">Std {q.standard}</Chip><Chip>{q.chapter}</Chip><Chip tone="amber">{q.difficulty}</Chip></div>
        <div className="text-xl font-medium"><Rich>{q.question}</Rich></div>
      </Card>
      {!res && (
        <Card className="space-y-4">
          <StepInput steps={steps} setSteps={setSteps} final={final} setFinal={setFinal} />
          {err && <p className="text-rose-600 text-sm">{err}</p>}
          <Btn disabled={busy || !final.trim()} onClick={submit}>{busy ? 'Analysing your working...' : 'Submit for diagnosis'}</Btn>
        </Card>)}
      {res && <Diagnosis res={res} />}
      {res && !res.intervention && res.next !== 'next_question' && <Btn variant="ghost" onClick={() => { setRes(null); setStage(null) }}>Add more working and try again</Btn>}
      {res && res.next === 'next_question' && <Btn onClick={() => goto('topics')}>Next question</Btn>}

      {iv && (stage === 'intervention' || stage === 'reintervene') && (
        <Card className="border-indigo-200 bg-indigo-50/40 space-y-3">
          <Chip tone="violet">Targeted intervention - {iv.type}</Chip>
          {res.explanation && <p className="leading-relaxed"><Rich>{res.explanation}</Rich></p>}
          <div className="rounded-xl bg-white border p-3"><div className="text-xs font-semibold text-slate-500 mb-1">THE CORRECT IDEA</div><Rich>{iv.correct_concept || iv.text}</Rich></div>
          <div className="rounded-xl bg-white border p-3"><div className="text-xs font-semibold text-slate-500 mb-1">WORKED EXAMPLE</div><Rich>{iv.worked_example}</Rich></div>
          <p className="text-sm text-slate-600"><b>Hint:</b> <Rich>{iv.hint}</Rich></p>
          {res.explanation_source && <p className="text-[11px] text-slate-400">Explanation source: {res.explanation_source}{iv.from_extension ? ' - extension case authored by the team' : ''}</p>}
          <Btn onClick={startReassess}>I've read this - test me again</Btn>
        </Card>)}
      {iv && stage === 'reassessment' && <StageCard title="Reassessment - a new question on the same idea" tone="blue" question={iv.reassessment_question} demo={demo?.reassessment} busy={busy} result={stageRes} onSubmit={(w, f) => sendStage('reassessment', w, f)} />}
      {iv && stage === 'transfer' && <StageCard title="Transfer - same idea, new form" tone="violet" question={iv.transfer_question} demo={demo?.transfer} busy={busy} result={stageRes} onSubmit={(w, f) => sendStage('transfer', w, f)} />}
      {stage === 'reintervene' && stageRes && <Banner tone="amber" title={stageRes.status_label}>{stageRes.message}</Banner>}
      {stage === 'done' && (
        <Banner tone="green" title="Misconception resolved">
          {stageRes?.message} <button className="underline font-semibold" onClick={() => goto('fingerprint')}>See your Misconception Fingerprint</button>
        </Banner>)}
      {err && res && <p className="text-rose-600 text-sm">{err}</p>}
    </div>
  )
}
