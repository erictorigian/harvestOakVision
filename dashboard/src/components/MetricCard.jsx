export default function MetricCard({ label, value, unit, sub, color }) {
  return (
    <div className="bg-[#162919] rounded-2xl p-4 flex flex-col gap-1 min-w-0" style={{ border: '1px solid rgba(61,145,72,0.15)' }}>
      <div className="text-[11px] font-medium text-[rgba(237,232,223,0.5)] uppercase tracking-wider leading-none">
        {label}
      </div>
      <div
        className={`font-bold leading-none mt-1.5 tabular-nums ${color || 'text-white'}`}
        style={{ fontSize: 'clamp(1.4rem, 2.2vw, 2rem)' }}
      >
        {value ?? '—'}
        {unit && (
          <span className="text-sm font-normal text-[rgba(237,232,223,0.35)] ml-1.5">{unit}</span>
        )}
      </div>
      {sub && (
        <div className="text-[11px] text-[rgba(237,232,223,0.35)] mt-0.5">{sub}</div>
      )}
    </div>
  )
}
