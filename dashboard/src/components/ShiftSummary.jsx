import { formatDuration } from '../utils'

function Row({ label, value, accent = false, sub }) {
  return (
    <div className="flex items-baseline justify-between py-2 border-b border-border/50 last:border-0">
      <span className="text-[#8B949E] font-mono text-xs tracking-wider uppercase">{label}</span>
      <div className="text-right">
        <span className={`font-mono font-semibold text-sm ${accent ? 'text-amber' : 'text-[#E6EDF3]'}`}>
          {value}
        </span>
        {sub && <span className="text-[#8B949E] font-mono text-xs ml-2">{sub}</span>}
      </div>
    </div>
  )
}

export default function ShiftSummary({ summary }) {
  if (!summary) return null

  const {
    total_pieces,
    pieces_per_hour_avg,
    peak_hour,
    peak_hour_pieces,
    total_downtime_seconds,
    downtime_pct,
    avg_speed_fpm,
    oee_availability,
  } = summary

  const target = parseInt(import.meta.env.VITE_TARGET_PPH || '450', 10)
  const variance = total_pieces - target * 8
  const variancePct = ((variance / (target * 8)) * 100).toFixed(1)

  const _HOUR_LABELS = [
    '12 AM','1 AM','2 AM','3 AM','4 AM','5 AM','6 AM','7 AM',
    '8 AM','9 AM','10 AM','11 AM','12 PM','1 PM','2 PM','3 PM',
    '4 PM','5 PM','6 PM','7 PM','8 PM','9 PM','10 PM','11 PM',
  ]

  return (
    <div className="bg-panel border border-border rounded-lg p-5">
      <div className="text-[10px] font-mono tracking-[0.2em] text-[#8B949E] uppercase mb-4">
        Shift Summary
      </div>

      <Row
        label="Total Pieces"
        value={total_pieces.toLocaleString()}
        accent
        sub={`${variance >= 0 ? '+' : ''}${variance} (${variancePct}%) vs target`}
      />
      <Row
        label="Pieces / Hour avg"
        value={pieces_per_hour_avg?.toFixed(0)}
        sub={`target ${target}`}
      />
      {peak_hour != null && (
        <Row
          label="Peak Hour"
          value={_HOUR_LABELS[peak_hour]}
          sub={`${peak_hour_pieces} pieces`}
        />
      )}
      <Row
        label="Total Downtime"
        value={formatDuration(total_downtime_seconds || 0)}
        sub={`${downtime_pct?.toFixed(1)}% of shift`}
      />
      <Row
        label="Avg Line Speed"
        value={`${avg_speed_fpm?.toFixed(1)} FPM`}
      />
      <Row
        label="OEE Availability"
        value={`${((oee_availability || 0) * 100).toFixed(1)}%`}
        accent
      />
    </div>
  )
}
