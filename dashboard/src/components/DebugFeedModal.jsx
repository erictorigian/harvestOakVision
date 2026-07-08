import { useEffect, useRef } from 'react'

const DEBUG_URL = `http://${window.location.hostname}:8080/debug_feed`

export default function DebugFeedModal({ open, onClose }) {
  const imgRef = useRef(null)

  useEffect(() => {
    if (!open && imgRef.current) {
      imgRef.current.src = ''
    }
  }, [open])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50 p-4"
      style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}
      onClick={onClose}
    >
      <div
        className="bg-[#2C2C2E] rounded-2xl overflow-hidden max-w-4xl w-full shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div
          className="flex items-center justify-between px-5 py-3.5"
          style={{ borderBottom: '1px solid rgba(84,84,88,0.4)' }}
        >
          <span className="text-[13px] font-semibold text-white">Debug Camera Feed</span>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full flex items-center justify-center text-[rgba(235,235,245,0.5)] hover:text-white transition-colors text-sm"
            style={{ background: 'rgba(255,255,255,0.08)' }}
          >
            ✕
          </button>
        </div>
        <div className="bg-black">
          <img
            ref={imgRef}
            src={DEBUG_URL}
            alt="Debug camera feed"
            className="w-full"
            onError={() => {}}
          />
        </div>
        <div className="px-5 py-3 text-[11px] text-[rgba(235,235,245,0.35)]">
          Green line = detection tripwire · Cyan box = belt ROI · dev= shows max deviation at tripwire
        </div>
      </div>
    </div>
  )
}
