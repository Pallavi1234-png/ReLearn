import React from 'react'
import katex from 'katex'

// ---- math rendering -------------------------------------------------------
export function toTex(s) {
  return String(s)
    .replace(/√\s*\(([^)]+)\)/g, '\\sqrt{$1}')
    .replace(/√\s*(\d+|[a-z])/g, '\\sqrt{$1}')
    .replace(/²/g, '^{2}').replace(/³/g, '^{3}').replace(/⁴/g, '^{4}')
    .replace(/\^\(([^)]+)\)/g, '^{$1}').replace(/\^(-?\d+)/g, '^{$1}')
    .replace(/×/g, '\\times ').replace(/÷/g, '\\div ').replace(/±/g, '\\pm ')
    .replace(/(-?\d+)\/(\d+)/g, '\\frac{$1}{$2}').replace(/\*/g, '\\cdot ')
    .replace(/α/g, '\\alpha ').replace(/β/g, '\\beta ')
}
const looksMath = (s) => !/[A-Za-z]{4,}/.test(s.replace(/sqrt/g, ''))
export function Tex({ children, block = false }) {
  const s = String(children ?? '')
  if (!looksMath(s)) return <span>{s}</span>
  try {
    const html = katex.renderToString(toTex(s), { throwOnError: false, displayMode: block })
    return <span dangerouslySetInnerHTML={{ __html: html }} />
  } catch { return <span>{s}</span> }
}
// renders prose with embedded math: words stay text, math-looking chunks get KaTeX
export function Rich({ children }) {
  const s = String(children ?? '')
  const parts = s.split(/(\s*[0-9a-z()+\-*/^=²³√.]*[0-9²³√^=][0-9a-z()+\-*/^=²³√.]*\s*)/gi)
  return <span>{parts.map((p, i) => (i % 2 ? <Tex key={i}>{p.trim()}</Tex> : <span key={i}>{p}</span>))}</span>
}

// ---- small building blocks ------------------------------------------------
export const Card = ({ className = '', children }) => (
  <div className={`rounded-2xl bg-white border border-slate-200 shadow-sm p-5 ${className}`}>{children}</div>
)
const TONES = {
  green: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  red: 'bg-rose-50 text-rose-800 border-rose-200',
  amber: 'bg-amber-50 text-amber-800 border-amber-200',
  blue: 'bg-sky-50 text-sky-800 border-sky-200',
  violet: 'bg-violet-50 text-violet-800 border-violet-200',
  slate: 'bg-slate-100 text-slate-700 border-slate-200',
}
export const Chip = ({ tone = 'slate', children }) => (
  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${TONES[tone]}`}>{children}</span>
)
export const Btn = ({ variant = 'primary', className = '', ...p }) => (
  <button {...p} className={`px-4 py-2 rounded-xl text-sm font-semibold transition disabled:opacity-40 ${
    variant === 'primary' ? 'bg-indigo-600 text-white hover:bg-indigo-700' :
    variant === 'ghost' ? 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50' :
    'bg-slate-900 text-white hover:bg-slate-700'} ${className}`} />
)
export const Banner = ({ tone, title, children }) => (
  <div className={`rounded-xl border p-4 ${TONES[tone]}`}>
    <div className="font-bold mb-1">{title}</div><div className="text-sm leading-relaxed">{children}</div>
  </div>
)
export const STATE_TONE = { New: 'amber', Improving: 'blue', Persistent: 'red', Resolved: 'green' }

// ---- handwriting canvas (OCR is a pluggable stub on the backend) ----------
export function DrawPad({ onExport }) {
  const ref = React.useRef(null)
  const drawing = React.useRef(false)
  const pos = (e) => { const r = ref.current.getBoundingClientRect(); return [(e.clientX - r.left) * (ref.current.width / r.width), (e.clientY - r.top) * (ref.current.height / r.height)] }
  const down = (e) => { drawing.current = true; const c = ref.current.getContext('2d'); const [x, y] = pos(e); c.beginPath(); c.moveTo(x, y); ref.current.setPointerCapture(e.pointerId) }
  const move = (e) => { if (!drawing.current) return; const c = ref.current.getContext('2d'); c.lineWidth = 3; c.lineCap = 'round'; c.strokeStyle = '#1e293b'; const [x, y] = pos(e); c.lineTo(x, y); c.stroke() }
  const up = () => { drawing.current = false }
  const clear = () => { const c = ref.current; c.getContext('2d').clearRect(0, 0, c.width, c.height) }
  return (
    <div>
      <canvas ref={ref} width={700} height={220} onPointerDown={down} onPointerMove={move} onPointerUp={up}
        className="w-full rounded-xl border-2 border-dashed border-slate-300 bg-white touch-none cursor-crosshair" />
      <div className="flex gap-2 mt-2">
        <Btn variant="ghost" onClick={clear}>Clear</Btn>
        <Btn variant="ghost" onClick={() => onExport(ref.current.toDataURL('image/png'))}>Read my handwriting</Btn>
      </div>
    </div>
  )
}
