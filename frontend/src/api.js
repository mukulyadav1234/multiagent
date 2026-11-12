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

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const data = await parseApiResponse(res).catch(() => null)
    const detail = Array.isArray(data?.detail) ? data.detail.map((d) => d.msg).join('; ') : data?.detail
    throw new Error(detail || `Request failed with status ${res.status}`)
  }
  return parseApiResponse(res)
}

export function startGeneration(payload) {
  return request('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export function getGeneration(generationId) {
  return request(`/api/generations/${generationId}`)
}

export function recompilePoster(payload) {
  return request('/api/recompile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export function exportUrl(generationId, format, scale) {
  return `${BASE}/api/artifacts/${generationId}/export?format=${format}&scale=${scale}`
}
