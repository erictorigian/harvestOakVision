import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import LiveMonitor from './pages/LiveMonitor'
import ShiftAnalytics from './pages/ShiftAnalytics'
import Settings from './pages/Settings'

const NAV = [
  { to: '/',       label: 'LIVE MONITOR' },
  { to: '/shift',  label: 'SHIFT ANALYTICS' },
  { to: '/settings', label: 'SETTINGS' },
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-surface text-[#E6EDF3]">
        {/* Top nav */}
        <nav className="border-b border-border bg-panel">
          <div className="flex items-center px-6 h-12 gap-8">
            <span className="font-mono font-bold text-amber tracking-widest text-sm uppercase">
              HARVEST OAK VISION
            </span>
            <div className="flex gap-1 ml-4">
              {NAV.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `px-4 py-1 text-xs font-mono tracking-wider rounded transition-colors ${
                      isActive
                        ? 'bg-amber/20 text-amber border border-amber/40'
                        : 'text-[#8B949E] hover:text-[#E6EDF3] hover:bg-white/5'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
          </div>
        </nav>

        {/* Page content */}
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
