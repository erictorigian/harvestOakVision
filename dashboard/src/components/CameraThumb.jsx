export default function CameraThumb({ frameB64, onClick }) {
  return (
    <div
      className="bg-panel border border-border rounded-lg p-5 flex flex-col cursor-pointer group"
      onClick={onClick}
    >
      <div className="text-[10px] font-mono tracking-[0.2em] text-[#8B949E] uppercase mb-4 flex items-center justify-between">
        <span>Camera Feed</span>
        <span className="text-[#8B949E] group-hover:text-amber transition-colors">&#x26F6; expand</span>
      </div>
      <div className="flex-1 flex items-center justify-center bg-black rounded overflow-hidden min-h-[140px]">
        {frameB64 ? (
          <img
            src={`data:image/jpeg;base64,${frameB64}`}
            alt="Camera feed"
            className="w-full h-full object-contain"
          />
        ) : (
          <span className="text-[#8B949E] font-mono text-xs">No feed — set DEBUG_OVERLAY=true</span>
        )}
      </div>
    </div>
  )
}
