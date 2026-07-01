import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  ResponsiveContainer, Cell,
} from 'recharts'

function barColor(pieces, target) {
  if (pieces === 0) return '#21262D'
  const pct = pieces / target
  if (pct >= 1.0) return '#10B981'    // green — at or above target
  if (pct >= 0.8) return '#F59E0B'    // amber — 80–99%
  return '#EF4444'                     // red — below 80%
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-panel border border-border rounded p-3 text-xs font-mono shadow-xl">
      <div className="text-amber font-bold mb-1">{label}</div>
      <div className="text-[#E6EDF3]">Pieces: <span className="text-amber">{d.pieces}</span></div>
      <div className="text-[#8B949E]">Target: {d.target}</div>
      <div className="text-[#8B949E]">Avg Speed: {d.avg_speed_fpm?.toFixed(1)} FPM</div>
      <div className="text-[#8B949E]">Downtime: {Math.round(d.downtime_seconds / 60)}m</div>
    </div>
  )
}

export default function HourlyChart({ data = [] }) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48 text-[#8B949E] font-mono text-sm">
        No hourly data yet
      </div>
    )
  }

  const target = data[0]?.target || 450

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#21262D" />
        <XAxis
          dataKey="hour_label"
          tick={{ fill: '#8B949E', fontSize: 11, fontFamily: 'JetBrains Mono' }}
          axisLine={{ stroke: '#30363D' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#8B949E', fontSize: 11, fontFamily: 'JetBrains Mono' }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
        <ReferenceLine y={target} stroke="#F59E0B" strokeDasharray="6 3" strokeOpacity={0.6} />
        <Bar dataKey="pieces" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={barColor(entry.pieces, entry.target)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
