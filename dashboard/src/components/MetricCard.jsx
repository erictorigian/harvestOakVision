/**
 * Large metric card — readable from 10 feet.
 * props: label, value, unit, sub, accent (color class)
 */
export default function MetricCard({ label, value, unit, sub, accent = 'text-amber' }) {
  return (
    <div className="bg-panel border border-border rounded-lg p-5 flex flex-col gap-1 min-w-0">
      <div className="text-[10px] font-mono tracking-[0.2em] text-[#8B949E] uppercase">
        {label}
      </div>
      <div className={`font-mono font-bold leading-none mt-1 ${accent}`} style={{ fontSize: 'clamp(2rem, 4vw, 3.5rem)' }}>
        {value ?? '—'}
        {unit && (
          <span className="text-lg font-normal text-[#8B949E] ml-1">{unit}</span>
        )}
      </div>
      {sub && (
        <div className="text-[11px] text-[#8B949E] font-mono mt-1">{sub}</div>
      )}
    </div>
  )
}
