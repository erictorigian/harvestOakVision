import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import LiveMonitor from './pages/LiveMonitor'
import ShiftAnalytics from './pages/ShiftAnalytics'
import Settings from './pages/Settings'

const NAV = [
  { to: '/',        label: 'Live Monitor' },
  { to: '/shift',   label: 'Shift Analytics' },
  { to: '/settings', label: 'Settings' },
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-[#0F1B11] text-[#EDE8DF]">
        <nav
          className="sticky top-0 z-40 border-b"
          style={{
            background: 'rgba(15,27,17,0.90)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderColor: 'rgba(61,145,72,0.25)',
          }}
        >
          <div className="flex items-center px-5 h-12 gap-5">
            <div className="flex items-center bg-white rounded-md px-2 py-1 h-7 flex-shrink-0">
              <img src="/harvest-oak-logo.png" alt="Harvest Oak" className="h-5 w-auto object-contain" />
            </div>
            <span className="text-[11px] font-medium tracking-widest uppercase text-[rgba(237,232,223,0.35)] select-none hidden sm:block">
              Production Monitor
            </span>
            <div className="flex gap-0.5 ml-auto">
              {NAV.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `px-3 py-1.5 text-[13px] rounded-lg transition-colors ${
                      isActive
                        ? 'font-medium'
                        : 'hover:bg-white/[0.05]'
                    }`
                  }
                  style={({ isActive }) => ({
                    color: isActive ? '#3572C6' : 'rgba(237,232,223,0.5)',
                    background: isActive ? 'rgba(53,114,198,0.12)' : undefined,
                  })}
                >
                  {label}
                </NavLink>
              ))}
            </div>
          </div>
        </nav>

        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<LiveMonitor />} />
            <Route path="/shift" element={<ShiftAnalytics />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
