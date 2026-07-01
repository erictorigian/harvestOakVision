/**
 * Horizontal timeline bar showing running vs downtime vs slow periods.
 * Uses the hourly data to build a visual shift timeline.
 */
export default function DowntimeWaterfall({ data = [] }) {
  if (!data.length) return null

  const totalSeconds = data.reduce(
    (sum, h) => sum + 3600,
    0
  )

  return (
    <div className="flex flex-col gap-2">
      <div className="text-[10px] font-mono tracking-widest text-[#8B949E] uppercase mb-1">
        Shift Timeline
      </div>
      <div className="flex h-8 rounded overflow-hidden gap-px">
        {data.map((hour, i) => {
          const downPct = Math.min(100, (hour.downtime_seconds / 3600) * 100)
          const runPct = 100 - downPct
          return (
            <div
              key={i}
              className="relative flex-1 flex flex-col overflow-hidden"
              title={`${hour.hour_label}: ${hour.pieces} pcs, ${Math.round(hour.downtime_seconds / 60)}m downtime`}
            >
              <div style={{ height: `${runPct}%` }} className="bg-emerald-600/60 w-full" />
              <div style={{ height: `${downPct}%` }} className="bg-red-500/70 w-full" />
            </div>
          )
        })}
      </div>
      <div className="flex gap-4 text-[10px] font-mono text-[#8B949E]">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-sm bg-emerald-600/60 inline-block" /> Running
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-sm bg-red-500/70 inline-block" /> Downtime
        </span>
      </div>
    </div>
  )
}
