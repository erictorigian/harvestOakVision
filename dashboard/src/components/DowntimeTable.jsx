import { formatTime, formatDuration } from '../utils'

const STATE_BADGE = {
  IDLE:    'bg-red-500/20 text-red-400 border-red-500/40',
  SLOW:    'bg-amber/20 text-amber border-amber/40',
  UNKNOWN: 'bg-[#30363D]/40 text-[#8B949E] border-[#30363D]',
}

export default function DowntimeTable({ events = [] }) {
  if (!events.length) {
    return (
      <div className="text-[#8B949E] font-mono text-sm text-center py-6">
        No downtime events today
      </div>
    )
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="text-[#8B949E] tracking-wider text-left border-b border-border">
            <th className="pb-2 pr-6">START</th>
            <th className="pb-2 pr-6">DURATION</th>
            <th className="pb-2 pr-6">STATE</th>
            <th className="pb-2">SNAPSHOT</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.id} className="border-b border-border/50 hover:bg-white/[0.02]">
              <td className="py-2 pr-6 text-[#E6EDF3]">
                {formatTime(ev.start_ts)}
              </td>
              <td className="py-2 pr-6 text-[#E6EDF3]">
                {ev.duration_seconds ? formatDuration(ev.duration_seconds) : (
                  <span className="text-red-400 animate-pulse">ACTIVE</span>
                )}
              </td>
              <td className="py-2 pr-6">
                <span className={`px-2 py-0.5 rounded border text-[10px] tracking-widest ${STATE_BADGE[ev.state] ?? STATE_BADGE.UNKNOWN}`}>
                  {ev.state}
                </span>
              </td>
              <td className="py-2">
                {ev.snapshot_path ? (
                  <span className="text-amber/70 cursor-pointer hover:text-amber text-[10px]">
                    [VIEW]
                  </span>
                ) : (
                  <span className="text-[#484F58]">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
