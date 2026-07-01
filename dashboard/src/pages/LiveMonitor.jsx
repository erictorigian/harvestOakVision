import { useState, useEffect } from 'react'
import useLiveMetrics from '../hooks/useLiveMetrics'
import { useDowntimeEvents } from '../hooks/useShiftData'
import MetricCard from '../components/MetricCard'
import StateBanner from '../components/StateBanner'
import PieceCounter from '../components/PieceCounter'
import DowntimeTable from '../components/DowntimeTable'
import DebugFeedModal from '../components/DebugFeedModal'
import CameraThumb from '../components/CameraThumb'
import { formatDuration } from '../utils'

function Clock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <span className="font-mono text-sm text-[#8B949E]">
      {now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

export default function LiveMonitor() {
  const { metrics, connected } = useLiveMetrics()
  const downtimeEvents = useDowntimeEvents()
  const [debugOpen, setDebugOpen] = useState(false)

  const m = metrics || {}
  const stateStartMs = m.timestamp ? Date.now() - 0 : 0
  const currentDuration = m.current_downtime_duration || 0

  return (
    <div className="p-2 flex flex-col gap-2 max-w-[1600px] mx-auto">

      {/* Top bar */}
      <div className="flex items-center justify-between">
        <div className="text-[9px] font-mono tracking-[0.2em] text-[#8B949E] uppercase">
          {m.shift_id ? `Shift #${m.shift_id}` : 'No Active Shift'}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-[10px] font-mono">
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
            <span className={connected ? 'text-emerald-400' : 'text-red-400'}>
              {connected ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>
          <Clock />
          <button
            onClick={() => setDebugOpen(true)}
            className="px-2 py-0.5 text-[9px] font-mono tracking-widest text-[#8B949E] border border-border rounded hover:border-amber/40 hover:text-amber transition-colors uppercase"
          >
            Debug
          </button>
        </div>
      </div>

      {/* State banner */}
      <StateBanner state={m.state || 'UNKNOWN'} durationSeconds={currentDuration} />

      {/* Hero metrics row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
        <MetricCard
          label="Total Pieces"
          value={(m.total_pieces_today || 0).toLocaleString()}
          sub="today"
          accent="text-amber"
        />
        <MetricCard
          label="Pieces / Hour"
          value={(m.pieces_per_hour_current || 0).toLocaleString()}
          sub="current rate"
          accent="text-amber"
        />
        <MetricCard
          label="Line Speed"
          value={(m.line_speed_fpm_smoothed || 0).toFixed(1)}
          unit="FPM"
          sub={`instant: ${(m.line_speed_fpm || 0).toFixed(1)} FPM`}
          accent="text-amber"
        />
        <MetricCard
          label="Outfeed Belt Speed"
          value={(m.outfeed_belt_speed_fpm_smoothed || 0).toFixed(1)}
          unit="FPM"
          sub={`instant: ${(m.outfeed_belt_speed_fpm || 0).toFixed(1)} FPM`}
          accent="text-amber"
        />
        <MetricCard
          label="Downtime Today"
          value={formatDuration(m.downtime_seconds_today || 0)}
          sub={m.state !== 'RUNNING' ? `current: ${formatDuration(currentDuration)}` : 'line running'}
          accent={m.downtime_seconds_today > 0 ? 'text-red-400' : 'text-emerald-400'}
        />
      </div>

      {/* Piece counter + camera thumbnail + downtime list */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
        <PieceCounter count={m.total_pieces_today || 0} />

        <CameraThumb
          frameB64={m.frame_debug_jpeg_b64 || null}
          onClick={() => setDebugOpen(true)}
        />

        <div className="bg-panel border border-border rounded p-3 flex flex-col">
          <div className="text-[9px] font-mono tracking-[0.2em] text-[#8B949E] uppercase mb-2">
            Downtime Events — Today
          </div>
          <div className="flex-1 overflow-auto">
            <DowntimeTable events={downtimeEvents} />
          </div>
        </div>
      </div>

      <DebugFeedModal open={debugOpen} onClose={() => setDebugOpen(false)} />
    </div>
  )
}
