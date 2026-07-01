export function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '0s'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function formatTime(isoString) {
  if (!isoString) return '—'
  const d = new Date(isoString)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function formatDate(isoString) {
  if (!isoString) return '—'
  const d = new Date(isoString)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
