const BASE = 'https://relearn-vtwm.onrender.com'
async function req(path, opts) {
  const r = await fetch(BASE + path, { headers: { 'Content-Type': 'application/json' }, ...opts })
  if (!r.ok) throw new Error((await r.text()) || r.statusText)
  return r.json()
}
export const api = {
  health: () => req('/api/health'),
  meta: () => req('/api/meta'),
  questions: (p) => req('/api/questions?' + new URLSearchParams(Object.fromEntries(Object.entries(p).filter(([, v]) => v)))),
  submit: (b) => req('/api/submit', { method: 'POST', body: JSON.stringify(b) }),
  interventionDone: (sid) => req(`/api/session/${sid}/intervention-done`, { method: 'POST' }),
  stage: (sid, stage, b) => req(`/api/session/${sid}/${stage}`, { method: 'POST', body: JSON.stringify(b) }),
  learner: (id) => req('/api/learner/' + id),
  map: () => req('/api/map'),
  evaluation: () => req('/api/evaluation'),
  demos: () => req('/api/demo-cases'),
  teacher: () => req('/api/teacher'),
  ocr: (image) => req('/api/ocr', { method: 'POST', body: JSON.stringify({ image }) }),
}
export const studentId = () => localStorage.getItem('relearn_student') || 'demo'
export const setStudentId = (v) => localStorage.setItem('relearn_student', v || 'demo')
