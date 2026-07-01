import { useState } from 'react'
import { useHourlyData, useShifts, useTodaySummary } from '../hooks/useShiftData'
import HourlyChart from '../components/HourlyChart'
import DowntimeWaterfall from '../components/DowntimeWaterfall'
import SpeedTrend from '../components/SpeedTrend'
import ShiftSummary from '../components/ShiftSummary'

function SectionLabel({ children }) {
  return (
    <div className="text-[10px] font-mono tracking-[0.2em] text-[#8B949E] uppercase mb-3">
      {children}
    </div>
  )
}

export default function ShiftAnalytics() {
  const [selectedDate, setSelectedDate] = useState('')
  const { data: hourly, loading } = useHourlyData(selectedDate || undefined)
  const { shifts } = useShifts()
  const today = useTodaySummary()

  const target = parseInt(import.meta.env.VITE_TARGET_PPH || '450', 10)

  return (
    <div className="p-5 flex flex-col gap-5 max-w-[1600px] mx-auto">

      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="font-mono text-sm text-[#E6EDF3] tracking-wider">
          SHIFT ANALYTICS
        </div>
        <div className="flex items-center gap-3">
          <label className="text-[10px] font-mono text-[#8B949E] uppercase tracking-wider">Date</label>
          <input
            type="date"
            value={selectedDate}
            onChange={e => setSelectedDate(e.target.value)}
            className="bg-panel border border-border rounded px-3 py-1 text-xs font-mono text-[#E6EDF3] focus:outline-none focus:border-amber/50"
          />
          {selectedDate && (
            <button
              onClick={() => setSelectedDate('')}
              className="text-[#8B949E] hover:text-amber font-mono text-xs"
            >
              Today
            </button>
          )}
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

        {/* Left — charts column */}
        <div className="xl:col-span-2 flex flex-col gap-5">

          {/* Hourly production chart */}
          <div className="bg-panel border border-border rounded-lg p-5">
            <SectionLabel>Pieces Per Hour</SectionLabel>
            {loading ? (
              <div className="h-48 flex items-center justify-center text-[#8B949E] font-mono text-sm">
                Loading...
              </div>
            ) : (
              <HourlyChart data={hourly} />
            )}
            <div className="mt-2 flex gap-4 text-[10px] font-mono text-[#8B949E]">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-emerald-500 inline-block" /> At/above target
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-amber inline-block" /> 80–99%
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-red-500 inline-block" /> Below 80%
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-px bg-amber/60 inline-block border-dashed border-t-2 border-amber/60" /> Target ({target}/hr)
              </span>
            </div>
          </div>

          {/* Speed trend */}
          <div className="bg-panel border border-border rounded-lg p-5">
            <SectionLabel>Line Speed Trend (FPM)</SectionLabel>
            <SpeedTrend data={hourly} />
          </div>

          {/* Downtime waterfall */}
          <div className="bg-panel border border-border rounded-lg p-5">
            <DowntimeWaterfall data={hourly} />
          </div>
        </div>

        {/* Right — summary column */}
        <div className="flex flex-col gap-5">
          <ShiftSummary summary={today} />

          {/* Shift history */}
          <div className="bg-panel border border-border rounded-lg p-5">
            <SectionLabel>Shift History</SectionLabel>
            <div className="flex flex-col gap-1 overflow-auto max-h-80">
              {shifts.length === 0 && (
                <div className="text-[#8B949E] font-mono text-xs">No shifts recorded yet</div>
              )}
              {shifts.map(s => (
                <button
                  key={s.id}
                  onClick={() => {
                    const d = new Date(s.start_ts)
                    setSelectedDate(d.toISOString().split('T')[0])
                  }}
                  className="flex justify-between items-center px-3 py-2 rounded hover:bg-white/[0.04] text-left transition-colors"
                >
                  <div>
                    <div className="text-xs font-mono text-[#E6EDF3]">{s.label || `Shift #${s.id}`}</div>
                    <div className="text-[10px] font-mono text-[#8B949E]">
                      {s.total_pieces?.toLocaleString()} pcs
                      {s.oee_availability && ` · OEE ${(s.oee_availability * 100).toFixed(0)}%`}
                    </div>
                  </div>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    s.end_ts
                      ? 'text-[#8B949E] border-border'
                      : 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
                  }`}>
                    {s.end_ts ? 'DONE' : 'ACTIVE'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
