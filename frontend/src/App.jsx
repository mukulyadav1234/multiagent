import React, { useEffect, useRef, useState } from 'react'
import { startGeneration, getGeneration, recompilePoster, exportUrl } from './api'

const panelStyle = {
  background: 'rgba(17,24,39,0.74)',
  border: '1px solid rgba(148,163,184,0.2)',
  boxShadow: '0 18px 45px rgba(15,23,42,0.45)',
  borderRadius: 20,
  backdropFilter: 'blur(10px)',
}

const inputStyle = {
  width: '100%',
  background: '#0f172a',
  color: '#e2e8f0',
  border: '1px solid rgba(148,163,184,0.2)',
  borderRadius: 12,
  padding: '10px 12px',
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
}

const SIZES = [
  { label: 'Auto (from prompt)', value: '' },
  { label: 'Portrait post 1080×1350', value: '1080x1350' },
  { label: 'Square 1080×1080', value: '1080x1080' },
  { label: 'Story / wallpaper 1080×1920', value: '1080x1920' },
  { label: 'Landscape 1920×1080', value: '1920x1080' },
  { label: 'Thumbnail 1280×720', value: '1280x720' },
  { label: 'A4 print 1240×1754', value: '1240x1754' },
]

const EXAMPLES = [
  'Happy Diwali poster with realistic glowing clay diyas, marigolds and a rangoli at night',
  'A photorealistic snow leopard on a Himalayan ridge at golden hour, phone wallpaper',
  'Product ad for a cold-brew coffee bottle with condensation drops, launching 1 December',
  'Birthday card for my sister Riya, soft pastel balloons and confetti',
]

const STAGES = [
  'Reading your request',
  'Planning the shot',
  'Painting the image',
  'Compiling and reviewing',
  'Fixing',
  'Rendering final',
]

// The current generation is kept per browser tab: it survives reloads and is
// forgotten when the tab/window closes or a new prompt is generated.
const SESSION_KEY = 'poster-studio:current'

function loadSession() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null')
  } catch {
    return null
  }
}

function saveSession(value) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(value))
  } catch {
    // Storage blocked (private mode etc.): the page still works, it just won't survive a reload.
  }
}

function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // ignore
  }
}

export default function App() {
  const [prompt, setPrompt] = useState(EXAMPLES[0])
  const [size, setSize] = useState('')
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [preview, setPreview] = useState(null)
  const [generationId, setGenerationId] = useState(null)
  const [result, setResult] = useState(null)
  const [htmlSource, setHtmlSource] = useState('')
  const [error, setError] = useState('')
  const timer = useRef(null)

  useEffect(() => () => clearInterval(timer.current), [])

  // Bring back the last generation (finished or still running) after a page reload.
  useEffect(() => {
    const saved = loadSession()
    if (!saved?.generationId) return
    setPrompt(saved.prompt ?? EXAMPLES[0])
    setSize(saved.size ?? '')
    followJob(saved.generationId, saved.startedAt || Date.now(), true)
  }, [])

  const onGenerate = async () => {
    const [width, height] = size ? size.split('x').map(Number) : [null, null]
    const startedAt = Date.now()
    setLoading(true)
    setError('')
    setStage('Starting')
    try {
      const { generation_id } = await startGeneration({ prompt, width, height })
      saveSession({ generationId: generation_id, prompt, size, startedAt })
      await followJob(generation_id, startedAt, false)
    } catch (e) {
      setError(e.message || 'Generation failed.')
      setLoading(false)
    }
  }

  // Poll a job until it finishes, then show it. `restoring` = resumed after a reload.
  const followJob = async (generation_id, startedAt, restoring) => {
    setLoading(true)
    setElapsed(Math.round((Date.now() - startedAt) / 1000))
    clearInterval(timer.current)
    timer.current = setInterval(() => setElapsed(Math.round((Date.now() - startedAt) / 1000)), 1000)
    try {
      let missedPolls = 0
      while (true) {
        let job
        try {
          job = await getGeneration(generation_id)
          missedPolls = 0
        } catch (e) {
          // A restored id the backend has never heard of (e.g. outputs deleted): forget it quietly.
          if (restoring && /not found/i.test(e.message)) {
            clearSession()
            return
          }
          // The backend is briefly unreachable while it reloads; keep waiting for ~20s.
          if (++missedPolls > 10) throw e
          await new Promise((r) => setTimeout(r, 2000))
          continue
        }
        if (job.stage) setStage(job.stage)
        if (job.status === 'error') throw new Error(job.error || 'Generation failed.')
        if (job.status === 'done') {
          setGenerationId(generation_id)
          setResult(job.result)
          setHtmlSource(job.result.html)
          setPreview(`/api/artifacts/${generation_id}/preview?${Date.now()}`)
          break
        }
        await new Promise((r) => setTimeout(r, 2000))
      }
    } catch (e) {
      setError(e.message || 'Generation failed.')
    } finally {
      clearInterval(timer.current)
      setLoading(false)
    }
  }

  const onRecompile = async () => {
    if (!generationId) return
    setLoading(true)
    setError('')
    setStage('Re-rendering your edit')
    try {
      await recompilePoster({ generation_id: generationId, html: htmlSource })
      setPreview(`/api/artifacts/${generationId}/preview?${Date.now()}`)
    } catch (e) {
      setError(e.message || 'Recompile failed.')
    } finally {
      setLoading(false)
    }
  }

  const stageIndex = STAGES.findIndex((s) => stage.startsWith(s))
  const lastReview = result?.reviews?.filter((r) => r.score).slice(-1)[0]
  const w = result?.width
  const h = result?.height

  const downloadLink = (label, format, scale, primary) => (
    <a
      key={label}
      href={exportUrl(generationId, format, scale)}
      style={{ background: primary ? '#1d4ed8' : '#334155', color: 'white', textDecoration: 'none', borderRadius: 10, padding: '10px 12px', fontSize: 14 }}
    >
      {label}
    </a>
  )

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(circle at top, #1e293b 0%, #0b1120 40%, #030712 100%)',
      color: '#e5eefb',
      fontFamily: 'Inter, Segoe UI, Arial, sans-serif',
      padding: '32px 16px',
    }}>
      <style>{`
        .studio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 860px) {
          .studio-grid { grid-template-columns: 1fr; }
        }
      `}</style>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ ...panelStyle, padding: '24px 24px 20px', marginBottom: 24 }}>
          <div style={{ fontSize: 12, letterSpacing: 2, textTransform: 'uppercase', color: '#94a3b8' }}>Brief → Creative Director → Code Writer → Render &amp; Review</div>
          <h1 style={{ margin: '8px 0 0', fontSize: 'clamp(1.8rem, 4vw, 3rem)', lineHeight: 1.1 }}>AI Poster Studio</h1>
        </div>

        <div className="studio-grid">
          <div style={{ ...panelStyle, padding: 22 }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: 12, color: '#dbeafe' }}>Describe any image</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Anything: a Diwali poster, a tiger at dawn, a product ad, a wallpaper, a birthday card…"
              style={{ ...inputStyle, minHeight: 150, resize: 'vertical', borderRadius: 16, padding: 16, fontSize: 16, lineHeight: 1.5 }}
            />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
              {EXAMPLES.map((ex) => (
                <button key={ex} onClick={() => setPrompt(ex)} disabled={loading} style={{ background: 'rgba(51,65,85,0.6)', color: '#cbd5e1', border: '1px solid rgba(148,163,184,0.25)', borderRadius: 999, padding: '6px 10px', fontSize: 12, cursor: 'pointer', textAlign: 'left' }}>
                  {ex.length > 48 ? ex.slice(0, 48) + '…' : ex}
                </button>
              ))}
            </div>

            <div style={{ marginTop: 16, maxWidth: 320 }}>
              <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 6 }}>Canvas size</div>
              <select value={size} onChange={(e) => setSize(e.target.value)} style={inputStyle}>
                {SIZES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 18, flexWrap: 'wrap' }}>
              <div style={{ fontSize: 13, color: '#94a3b8' }}>Usually 2–5 minutes: the image is planned, painted in code, then reviewed and fixed.</div>
              <button
                onClick={onGenerate}
                disabled={loading || !prompt.trim()}
                style={{
                  background: 'linear-gradient(135deg, #f59e0b, #f97316)',
                  color: '#111827',
                  border: 'none',
                  borderRadius: 12,
                  padding: '12px 20px',
                  fontWeight: 700,
                  fontSize: 15,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.7 : 1,
                }}
              >
                {loading ? 'Working…' : 'Generate'}
              </button>
            </div>

            {loading && (
              <div style={{ marginTop: 18 }}>
                {STAGES.map((s, i) => (
                  <div key={s} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '4px 0', color: i < stageIndex ? '#86efac' : i === stageIndex ? '#fbbf24' : '#64748b', fontSize: 14 }}>
                    <span style={{ width: 14 }}>{i < stageIndex ? '✓' : i === stageIndex ? '●' : '○'}</span>
                    {i === stageIndex ? stage : s}
                  </div>
                ))}
                {stageIndex === -1 && <div style={{ color: '#fbbf24', fontSize: 14 }}>{stage}</div>}
                <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 6 }}>{elapsed}s elapsed</div>
              </div>
            )}

            {error && (
              <div style={{ marginTop: 18, background: 'rgba(127,29,29,0.35)', color: '#fecaca', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 12, padding: '10px 12px', overflowWrap: 'anywhere' }}>
                {error}
              </div>
            )}

            {result && !loading && (
              <div style={{ marginTop: 18, fontSize: 14, color: '#cbd5e1', lineHeight: 1.5 }}>
                <div style={{ fontWeight: 700, color: '#e2e8f0' }}>{result.creative?.concept_name}</div>
                <div>{result.creative?.concept}</div>
                {lastReview && <div style={{ marginTop: 8, color: '#94a3b8' }}>Reviewer score {lastReview.score}/10 — {lastReview.summary}</div>}
              </div>
            )}
          </div>

          <div style={{ ...panelStyle, padding: 22 }}>
            <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 16 }}>Preview {w ? <span style={{ fontWeight: 400, fontSize: 13, color: '#94a3b8' }}>{w}×{h}</span> : null}</div>
            {preview ? (
              <div>
                <img src={preview} alt="Generated image" style={{ width: '100%', borderRadius: 16, border: '1px solid rgba(148,163,184,0.2)', background: '#020617' }} />
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
                  {downloadLink(`PNG 2× (${w * 2}×${h * 2})`, 'png', 2, true)}
                  {downloadLink(`PNG 4× (${w * 4}×${h * 4})`, 'png', 4, true)}
                  {downloadLink('JPG 2×', 'jpeg', 2)}
                  {downloadLink('PDF (vector)', 'pdf', 1)}
                  <a href={`/api/artifacts/${generationId}/source`} target="_blank" rel="noreferrer" style={{ background: '#334155', color: 'white', textDecoration: 'none', borderRadius: 10, padding: '10px 12px', fontSize: 14 }}>HTML</a>
                </div>
              </div>
            ) : (
              <div style={{ minHeight: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', border: '1px dashed rgba(148,163,184,0.4)', borderRadius: 16, textAlign: 'center', padding: 16 }}>
                Your image will appear here.
              </div>
            )}
          </div>
        </div>

        {preview && (
          <div style={{ ...panelStyle, marginTop: 24, padding: 22 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>Source editor</h3>
              <button
                onClick={onRecompile}
                disabled={loading}
                style={{
                  background: '#0f172a',
                  color: '#e2e8f0',
                  border: '1px solid rgba(148,163,184,0.35)',
                  borderRadius: 12,
                  padding: '10px 16px',
                  fontWeight: 600,
                  cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                Recompile
              </button>
            </div>
            <textarea
              value={htmlSource}
              onChange={(e) => setHtmlSource(e.target.value)}
              style={{
                width: '100%',
                minHeight: 320,
                borderRadius: 16,
                border: '1px solid rgba(148,163,184,0.2)',
                background: '#0f172a',
                color: '#dbeafe',
                padding: 18,
                boxSizing: 'border-box',
                resize: 'vertical',
                fontFamily: 'ui-monospace, SFMono-Regular, monospace',
                fontSize: 13,
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
