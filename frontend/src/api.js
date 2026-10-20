async function parseApiResponse(res) {
  const text = await res.text()
  if (!text) {
    throw new Error('Empty response from backend.')
  }

  try {
    return JSON.parse(text)
  } catch (err) {
    throw new Error(text.slice(0, 300) || 'Invalid JSON response from backend.')
  }
}

const BASE = import.meta.env.VITE_BACKEND_BASE || ''

export async function generatePoster(payload) {
  const res = await fetch(`${BASE}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const data = await parseApiResponse(res).catch(() => null)
    throw new Error(data?.detail || `Request failed with status ${res.status}`)
  }

  return parseApiResponse(res)
}

export async function recompilePoster(payload) {
  const res = await fetch(`${BASE}/api/recompile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const data = await parseApiResponse(res).catch(() => null)
    throw new Error(data?.detail || `Request failed with status ${res.status}`)
  }

  return parseApiResponse(res)
}
