import { formatTime, formatDuration } from '../utils'

const STATE_STYLE = {
  IDLE:    { bg: 'rgba(255,69,58,0.12)',   text: '#FF453A' },
  SLOW:    { bg: 'rgba(255,159,10,0.12)',  text: '#FF9F0A' },
  UNKNOWN: { bg: 'rgba(255,255,255,0.06)', text: 'rgba(235,235,245,0.35)' },
}

export default function DowntimeTable({ events = [] }) {
  if (!events.length) {
    return (
      <div className="text-[rgba(235,235,245,0.3)] text-sm text-center py-8">
        No downtime events today
      </div>
    )
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-[13px]">
        <thead>
          <tr
            className="text-[11px] font-medium text-[rgba(235,235,245,0.4)] uppercase tracking-wider text-left"
            style={{ borderBottom: '1px solid rgba(84,84,88,0.4)' }}
          >
            <th className="pb-2 pr-5 font-medium">Start</th>
            <th className="pb-2 pr-5 font-medium">Duration</th>
            <th className="pb-2 pr-4 font-medium">State</th>
            <th className="pb-2 font-medium">Snap</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => {
            const s = STATE_STYLE[ev.state] ?? STATE_STYLE.UNKNOWN
            return (
              <tr
                key={ev.id}
                className="hover:bg-white/[0.03] transition-colors"
                style={{ borderBottom: '1px solid rgba(84,84,88,0.2)' }}
              >
                <td className="py-2.5 pr-5 text-[rgba(235,235,245,0.85)] tabular-nums">
                  {formatTime(ev.start_ts)}
                </td>
                <td className="py-2.5 pr-5 tabular-nums">
                  {ev.duration_seconds ? (
                    <span className="text-[rgba(235,235,245,0.85)]">{formatDuration(ev.duration_seconds)}</span>
                  ) : (
                    <span className="text-[#FF453A] font-medium">Active</span>
                  )}
                </td>
                <td className="py-2.5 pr-4">
                  <span
                    className="px-2 py-0.5 rounded-md text-[11px] font-medium"
                    style={{ background: s.bg, color: s.text }}
                  >
                    {ev.state}
                  </span>
                </td>
                <td className="py-2.5">
                  {ev.snapshot_path ? (
                    <span className="text-[#0A84FF] text-[11px] cursor-pointer hover:text-[#409CFF] transition-colors">
                      View
                    </span>
                  ) : (
                    <span className="text-[rgba(235,235,245,0.2)]">—</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
