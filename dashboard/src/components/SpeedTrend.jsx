import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-panel border border-border rounded p-3 text-xs font-mono shadow-xl">
      <div className="text-[#8B949E] mb-1">{label}</div>
      <div className="text-amber">
        {payload[0]?.value?.toFixed(1)} FPM
      </div>
    </div>
  )
}

export default function SpeedTrend({ data = [], targetFpm }) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-40 text-[#8B949E] font-mono text-sm">
        No speed data yet
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
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
          domain={['auto', 'auto']}
        />
        <Tooltip content={<CustomTooltip />} />
        {targetFpm && (
          <ReferenceLine y={targetFpm} stroke="#F59E0B" strokeDasharray="6 3" strokeOpacity={0.5} />
        )}
        <Line
          type="monotone"
          dataKey="avg_speed_fpm"
          stroke="#F59E0B"
          strokeWidth={2}
          dot={{ fill: '#F59E0B', r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
