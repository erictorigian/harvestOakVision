export default function CameraThumb({ frameB64, onClick }) {
  return (
    <div
      className="bg-[#2C2C2E] rounded-2xl overflow-hidden cursor-pointer group flex flex-col"
      onClick={onClick}
    >
      <div
        className="flex items-center justify-between px-4 py-3 flex-shrink-0"
        style={{ borderBottom: '1px solid rgba(84,84,88,0.4)' }}
      >
        <span className="text-[11px] font-medium text-[rgba(235,235,245,0.5)] uppercase tracking-wider">
          Camera Feed
        </span>
        <span className="text-[11px] text-[rgba(235,235,245,0.25)] group-hover:text-[rgba(235,235,245,0.55)] transition-colors">
          Expand ↗
        </span>
      </div>
      <div className="bg-black flex-1 flex items-start justify-center min-h-[140px]">
        {frameB64 ? (
          <img
            src={`data:image/jpeg;base64,${frameB64}`}
            alt="Camera feed"
            className="w-full h-full object-contain object-top"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-40">
            <span className="text-[rgba(235,235,245,0.25)] text-sm">
              No feed — set DEBUG_OVERLAY=true
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
