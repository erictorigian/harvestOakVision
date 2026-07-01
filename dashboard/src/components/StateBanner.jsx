import { formatDuration } from '../utils'

const STATE_CONFIG = {
  RUNNING: { bg: 'bg-emerald-500/20', border: 'border-emerald-500/60', text: 'text-emerald-400', dot: 'bg-emerald-400', label: 'RUNNING' },
  SLOW:    { bg: 'bg-amber/20',       border: 'border-amber/60',       text: 'text-amber',       dot: 'bg-amber',       label: 'SLOW — POSSIBLE JAM' },
  IDLE:    { bg: 'bg-red-500/20',     border: 'border-red-500/60',     text: 'text-red-400',     dot: 'bg-red-400',     label: 'IDLE — LINE STOPPED' },
  UNKNOWN: { bg: 'bg-[#30363D]/40',   border: 'border-[#30363D]',      text: 'text-[#8B949E]',   dot: 'bg-[#8B949E]',   label: 'UNKNOWN' },
}

export default function StateBanner({ state = 'UNKNOWN', durationSeconds = 0 }) {
  const cfg = STATE_CONFIG[state] ?? STATE_CONFIG.UNKNOWN
  const duration = formatDuration(durationSeconds)

  return (
    <div className={`border rounded px-3 py-1.5 flex items-center gap-2 ${cfg.bg} ${cfg.border}`}>
      <span className={`w-2 h-2 rounded-full animate-pulse flex-shrink-0 ${cfg.dot}`} />
      <span className={`font-mono font-bold tracking-widest text-xs ${cfg.text}`}>
        {cfg.label}
      </span>
      <span className="text-[#8B949E] font-mono text-xs ml-auto">
        {duration}
      </span>
    </div>
  )
}
