import { formatDuration } from '../utils'

const STATE = {
  RUNNING: {
    bg: 'rgba(61,145,72,0.12)',
    border: 'rgba(61,145,72,0.35)',
    dot: '#3D9148',
    text: '#5DB869',
    label: 'Running',
    pulse: true,
  },
  SLOW: {
    bg: 'rgba(210,140,30,0.1)',
    border: 'rgba(210,140,30,0.3)',
    dot: '#D28C1E',
    text: '#E0A030',
    label: 'Slow — Possible Jam',
    pulse: false,
  },
  IDLE: {
    bg: 'rgba(200,82,42,0.1)',
    border: 'rgba(200,82,42,0.3)',
    dot: '#C8522A',
    text: '#E06040',
    label: 'Idle — Line Stopped',
    pulse: false,
  },
  UNKNOWN: {
    bg: 'rgba(255,255,255,0.02)',
    border: 'rgba(61,145,72,0.2)',
    dot: 'rgba(237,232,223,0.25)',
    text: 'rgba(237,232,223,0.35)',
    label: 'Unknown',
    pulse: false,
  },
}

export default function StateBanner({ state = 'UNKNOWN', durationSeconds = 0 }) {
  const cfg = STATE[state] ?? STATE.UNKNOWN

  return (
    <div
      className="rounded-2xl px-4 py-3 flex items-center gap-3 border"
      style={{ background: cfg.bg, borderColor: cfg.border }}
    >
      <span
        className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.pulse ? 'animate-pulse' : ''}`}
        style={{ background: cfg.dot }}
      />
      <span className="text-[13px] font-semibold" style={{ color: cfg.text }}>
        {cfg.label}
      </span>
      {durationSeconds > 0 && (
        <span className="text-[13px] text-[rgba(237,232,223,0.35)] ml-auto tabular-nums">
          {formatDuration(durationSeconds)}
        </span>
      )}
    </div>
  )
}
