import { useEffect, useRef, useState } from 'react'

export default function PieceCounter({ count = 0 }) {
  const prevRef = useRef(count)
  const [flash, setFlash] = useState(false)

  useEffect(() => {
    if (count !== prevRef.current) {
      prevRef.current = count
      setFlash(true)
      const t = setTimeout(() => setFlash(false), 500)
      return () => clearTimeout(t)
    }
  }, [count])

  return (
    <div className="bg-[#2C2C2E] rounded-2xl p-6 flex flex-col items-center justify-start">
      <div className="text-[11px] font-medium text-[rgba(235,235,245,0.5)] uppercase tracking-wider mb-4">
        Total Pieces Today
      </div>
      <div
        className={`font-bold leading-none tabular-nums ${flash ? 'count-flash' : 'text-white'}`}
        style={{ fontSize: 'clamp(3rem, 6vw, 5rem)' }}
      >
        {count.toLocaleString()}
      </div>
      <div className="text-[11px] text-[rgba(235,235,245,0.25)] mt-4 uppercase tracking-widest">
        Pieces Counted
      </div>
    </div>
  )
}
