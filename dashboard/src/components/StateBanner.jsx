import { formatDuration } from '../utils'

const STATE = {
  RUNNING: {
    bg: 'rgba(48,209,88,0.1)',
    border: 'rgba(48,209,88,0.3)',
    dot: '#30D158',
    text: '#30D158',
    label: 'Running',
    pulse: true,
  },
  SLOW: {
    bg: 'rgba(255,159,10,0.1)',
    border: 'rgba(255,159,10,0.3)',
    dot: '#FF9F0A',
    text: '#FF9F0A',
    label: 'Slow — Possible Jam',
    pulse: false,
  },
  IDLE: {
    bg: 'rgba(255,69,58,0.1)',
    border: 'rgba(255,69,58,0.3)',
    dot: '#FF453A',
    text: '#FF453A',
    label: 'Idle — Line Stopped',
    pulse: false,
  },
  UNKNOWN: {
    bg: 'rgba(255,255,255,0.03)',
    border: 'rgba(84,84,88,0.4)',
    dot: 'rgba(235,235,245,0.3)',
    text: 'rgba(235,235,245,0.35)',
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
        <span className="text-[13px] text-[rgba(235,235,245,0.35)] ml-auto tabular-nums">
          {formatDuration(durationSeconds)}
        </span>
      )}
    </div>
  )
}
