import React, { useState } from 'react'
import { generatePoster, recompilePoster } from './api'

const panelStyle = {
  background: 'rgba(17,24,39,0.74)',
  border: '1px solid rgba(148,163,184,0.2)',
  boxShadow: '0 18px 45px rgba(15,23,42,0.45)',
  borderRadius: 20,
  backdropFilter: 'blur(10px)',
}

export default function App() {
  const [prompt, setPrompt] = useState('Create a Happy Diwali poster for NIIT.')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)
  const [generationId, setGenerationId] = useState(null)
  const [htmlSource, setHtmlSource] = useState('')
  const [error, setError] = useState('')

  const onGenerate = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await generatePoster({ prompt })
      if (res.detail) throw new Error(res.detail)
      if (res.generation_id) {
        setGenerationId(res.generation_id)
        setPreview(res.preview_url)
        setHtmlSource(res.html)
      }
    } catch (e) {
      setError(e.message || 'Generation failed.')
    } finally {
      setLoading(false)
    }
  }

  const onRecompile = async () => {
    if (!generationId) return
    setLoading(true)
    setError('')
    try {
      await recompilePoster({ generation_id: generationId, html: htmlSource, format: 'png' })
      setPreview(`/api/artifacts/${generationId}/preview?${Date.now()}`)
    } catch (e) {
      setError(e.message || 'Recompile failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(circle at top, #1e293b 0%, #0b1120 40%, #030712 100%)',
      color: '#e5eefb',
      fontFamily: 'Inter, Segoe UI, Arial, sans-serif',
      padding: '32px 18px',
    }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ ...panelStyle, padding: '28px 28px 20px', marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 12, letterSpacing: 2, textTransform: 'uppercase', color: '#94a3b8' }}>Creative automation</div>
              <h1 style={{ margin: '8px 0 0', fontSize: 'clamp(2rem, 4vw, 3.2rem)', lineHeight: 1.1 }}>AI Marketing Studio</h1>
            </div>
            <div style={{
              padding: '10px 18px',
              borderRadius: 999,
              border: '1px solid rgba(217,119,6,0.5)',
              background: 'rgba(245,158,11,0.08)',
              color: '#fbbf24',
              fontSize: 12,
              letterSpacing: 1.2,
              textTransform: 'uppercase',
            }}>
              Poster Generator
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 24 }}>
          <div style={{ ...panelStyle, padding: 22 }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: 12, color: '#dbeafe' }}>Describe the poster</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Create a Happy Diwali poster for NIIT."
              style={{
                width: '100%',
                minHeight: 160,
                resize: 'vertical',
                background: '#0f172a',
                color: '#e2e8f0',
                border: '1px solid rgba(148,163,184,0.2)',
                borderRadius: 16,
                padding: 18,
                fontSize: 16,
                lineHeight: 1.5,
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 18, flexWrap: 'wrap' }}>
              <div style={{ fontSize: 14, color: '#94a3b8' }}>Generated poster dimensions are handled on the backend.</div>
              <button
                onClick={onGenerate}
                disabled={loading}
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
                {loading ? 'Generating...' : 'Generate Poster'}
              </button>
            </div>

            {error && (
              <div style={{ marginTop: 18, background: 'rgba(127,29,29,0.35)', color: '#fecaca', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 12, padding: '10px 12px' }}>
                {error}
              </div>
            )}
          </div>

          <div style={{ ...panelStyle, padding: 22 }}>
            <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 16 }}>Poster preview</div>
            {preview ? (
              <div>
                <img src={preview} alt="Poster preview" style={{ width: '100%', borderRadius: 16, border: '1px solid rgba(148,163,184,0.2)', background: '#020617' }} />
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 14 }}>
                  <a href={`/api/artifacts/${generationId}/download?filename=poster.png`} target="_blank" rel="noreferrer" style={{ background: '#1d4ed8', color: 'white', textDecoration: 'none', borderRadius: 10, padding: '10px 12px' }}>Download PNG</a>
                  <a href={`/api/artifacts/${generationId}/source`} target="_blank" rel="noreferrer" style={{ background: '#334155', color: 'white', textDecoration: 'none', borderRadius: 10, padding: '10px 12px' }}>Download HTML</a>
                </div>
              </div>
            ) : (
              <div style={{ minHeight: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', border: '1px dashed rgba(148,163,184,0.4)', borderRadius: 16 }}>
                Generate a poster to see the preview here.
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
                Recompile Poster
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
