import { useEffect, useRef, useState } from 'react'

export default function PieceCounter({ count = 0 }) {
  const prevRef = useRef(count)
  const [flash, setFlash] = useState(false)

  useEffect(() => {
    if (count !== prevRef.current) {
      prevRef.current = count
      setFlash(true)
      const t = setTimeout(() => setFlash(false), 400)
      return () => clearTimeout(t)
    }
  }, [count])

  return (
    <div className="flex flex-col items-center justify-center bg-panel border border-border rounded p-4">
      <div className="text-[9px] font-mono tracking-[0.2em] text-[#8B949E] uppercase mb-1">
        Total Pieces Today
      </div>
      <div
        className={`font-mono font-bold transition-all duration-200 ${
          flash ? 'count-flash' : 'text-amber'
        }`}
        style={{ fontSize: 'clamp(2.5rem, 5vw, 4rem)', lineHeight: 1 }}
      >
        {count.toLocaleString()}
      </div>
      <div className="text-[#8B949E] font-mono text-[9px] mt-1 tracking-wider">
        PIECES COUNTED
      </div>
    </div>
  )
}
