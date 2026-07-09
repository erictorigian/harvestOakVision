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
    <span className="text-[13px] text-[rgba(235,235,245,0.4)] tabular-nums">
      {now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

export default function LiveMonitor() {
  const { metrics, connected } = useLiveMetrics()
  const downtimeEvents = useDowntimeEvents()
  const [debugOpen, setDebugOpen] = useState(false)

  const m = metrics || {}
  const currentDuration = m.current_downtime_duration || 0

  return (
    <div className="p-4 flex flex-col gap-3 max-w-[1600px] mx-auto">

      {/* Top bar */}
      <div className="flex items-center justify-between px-1 pt-1">
        <div className="text-[12px] text-[rgba(235,235,245,0.35)]">
          {m.shift_id ? `Shift #${m.shift_id}` : 'No Active Shift'}
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${connected ? 'animate-pulse' : ''}`}
              style={{ background: connected ? '#3D9148' : '#C8522A' }}
            />
            <span className="text-[12px]" style={{ color: connected ? 'rgba(237,232,223,0.5)' : '#C8522A' }}>
              {connected ? 'Live' : 'Disconnected'}
            </span>
          </div>
          <Clock />
          <button
            onClick={() => setDebugOpen(true)}
            className="px-3 py-1 text-[12px] rounded-lg transition-colors"
            style={{
              border: '1px solid rgba(84,84,88,0.6)',
              color: 'rgba(235,235,245,0.4)',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = '#fff'; e.currentTarget.style.borderColor = 'rgba(84,84,88,0.9)' }}
            onMouseLeave={e => { e.currentTarget.style.color = 'rgba(235,235,245,0.4)'; e.currentTarget.style.borderColor = 'rgba(84,84,88,0.6)' }}
          >
            Debug
          </button>
        </div>
      </div>

      {/* State banner */}
      <StateBanner state={m.state || 'UNKNOWN'} durationSeconds={currentDuration} />

      {/* Metrics row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <MetricCard
          label="Total Pieces"
          value={(m.total_pieces_today || 0).toLocaleString()}
          sub="today"
        />
        <MetricCard
          label="Pieces / Hour"
          value={(m.pieces_per_hour_current || 0).toLocaleString()}
          sub="current rate"
        />
        <MetricCard
          label="Line Speed"
          value={(m.line_speed_fpm_smoothed || 0).toFixed(1)}
          unit="FPM"
          sub={`instant: ${(m.line_speed_fpm || 0).toFixed(1)} FPM`}
        />
        <MetricCard
          label="Outfeed Belt"
          value={(m.outfeed_belt_speed_fpm_smoothed || 0).toFixed(1)}
          unit="FPM"
          sub={`instant: ${(m.outfeed_belt_speed_fpm || 0).toFixed(1)} FPM`}
        />
        <MetricCard
          label="Downtime Today"
          value={formatDuration(m.downtime_seconds_today || 0)}
          sub={m.state !== 'RUNNING' ? `current: ${formatDuration(currentDuration)}` : 'line running'}
          color={(m.downtime_seconds_today || 0) > 0 ? 'text-[#E06040]' : 'text-[#5DB869]'}
        />
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <PieceCounter count={m.total_pieces_today || 0} />

        <CameraThumb
          frameB64={m.frame_debug_jpeg_b64 || null}
          onClick={() => setDebugOpen(true)}
        />

        <div className="bg-[#162919] rounded-2xl p-4 flex flex-col" style={{ border: '1px solid rgba(61,145,72,0.15)' }}>
          <div className="text-[11px] font-medium text-[rgba(237,232,223,0.5)] uppercase tracking-wider mb-3 flex-shrink-0">
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
