export default function MetricCard({ label, value, unit, sub, accent = 'text-amber' }) {
  return (
    <div className="bg-panel border border-border rounded p-3 flex flex-col gap-0.5 min-w-0">
      <div className="text-[9px] font-mono tracking-[0.15em] text-[#8B949E] uppercase">
        {label}
      </div>
      <div className={`font-mono font-bold leading-none mt-0.5 ${accent}`} style={{ fontSize: 'clamp(1.25rem, 2vw, 2rem)' }}>
        {value ?? '—'}
        {unit && (
          <span className="text-xs font-normal text-[#8B949E] ml-1">{unit}</span>
        )}
      </div>
      {sub && (
        <div className="text-[9px] text-[#8B949E] font-mono">{sub}</div>
      )}
    </div>
  )
}
