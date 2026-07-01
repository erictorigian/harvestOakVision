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
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-panel border border-border rounded-lg overflow-hidden max-w-4xl w-full"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <span className="font-mono text-xs text-[#8B949E] tracking-widest uppercase">
            Debug Feed — Camera View
          </span>
          <button
            onClick={onClose}
            className="text-[#8B949E] hover:text-[#E6EDF3] font-mono text-lg leading-none"
          >
            ✕
          </button>
        </div>
        <div className="p-2 bg-black">
          <img
            ref={imgRef}
            src={DEBUG_URL}
            alt="Debug camera feed"
            className="w-full rounded"
            onError={() => {}}
          />
        </div>
        <div className="px-4 py-2 text-[10px] font-mono text-[#8B949E]">
          Yellow line = detection line &nbsp;·&nbsp; Green boxes = active contours &nbsp;·&nbsp;
          Enable DEBUG_OVERLAY=true in .env to activate
        </div>
      </div>
    </div>
  )
}
