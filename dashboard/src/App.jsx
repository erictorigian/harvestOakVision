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
      <div className="min-h-screen flex flex-col bg-[#1C1C1E] text-white">
        <nav
          className="sticky top-0 z-40 border-b"
          style={{
            background: 'rgba(28,28,30,0.85)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderColor: 'rgba(84,84,88,0.45)',
          }}
        >
          <div className="flex items-center px-5 h-12 gap-6">
            <span className="text-[13px] font-semibold tracking-tight text-white select-none">
              Harvest Oak Vision
            </span>
            <div className="flex gap-0.5">
              {NAV.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `px-3 py-1.5 text-[13px] rounded-lg transition-colors ${
                      isActive
                        ? 'bg-white/[0.12] text-white font-medium'
                        : 'text-[rgba(235,235,245,0.55)] hover:text-white hover:bg-white/[0.06]'
                    }`
                  }
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
