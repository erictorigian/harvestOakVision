import { useState, useEffect } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SEP = { borderBottom: '1px solid rgba(84,84,88,0.35)' }

function Field({ label, name, value, onChange, type = 'text', min, max, step, hint }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[11px] font-medium text-[rgba(235,235,245,0.5)] uppercase tracking-wider">
        {label}
      </label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={e => onChange(name, e.target.value)}
        min={min}
        max={max}
        step={step}
        className="bg-[#3A3A3C] rounded-xl px-3 py-2.5 text-[13px] text-white border-0 focus:outline-none focus:ring-2 focus:ring-[#0A84FF]/50 w-full transition-shadow placeholder-white/20"
      />
      {hint && <div className="text-[11px] text-[rgba(235,235,245,0.25)]">{hint}</div>}
    </div>
  )
}

function RangeField({ label, name, value, onChange, min, max, step = 1, unit, hint }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-baseline">
        <label className="text-[11px] font-medium text-[rgba(235,235,245,0.5)] uppercase tracking-wider">
          {label}
        </label>
        <span className="text-[13px] font-semibold text-white tabular-nums">{value}{unit}</span>
      </div>
      <input
        type="range"
        name={name}
        value={value}
        onChange={e => onChange(name, e.target.value)}
        min={min}
        max={max}
        step={step}
        className="w-full accent-[#0A84FF] h-1"
      />
      {hint && <div className="text-[11px] text-[rgba(235,235,245,0.25)]">{hint}</div>}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="bg-[#2C2C2E] rounded-2xl overflow-hidden">
      <div
        className="px-5 py-3"
        style={SEP}
      >
        <span className="text-[11px] font-semibold text-[rgba(235,235,245,0.4)] uppercase tracking-wider">
          {title}
        </span>
      </div>
      <div className="px-5 py-4 flex flex-col gap-5">
        {children}
      </div>
    </div>
  )
}

export default function Settings() {
  const [form, setForm] = useState({
    camera_rtsp_url: '',
    detection_line_y_percent: '50',
    min_contour_area: '2000',
    count_cooldown_ms: '800',
    conveyor_visible_feet: '8.0',
    downtime_threshold_seconds: '45',
    target_pieces_per_hour: '450',
    shift_day_start: '06:00',
    shift_aft_start: '14:00',
    shift_night_start: '22:00',
  })
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)
  const [testing, setTesting] = useState(false)
  const [resetConfirm, setResetConfirm] = useState(false)
  const [resetMsg, setResetMsg] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/settings`)
      .then(r => r.json())
      .then(data => setForm(prev => ({ ...prev, ...data })))
      .catch(() => {})
  }, [])

  const set = (name, value) => setForm(f => ({ ...f, [name]: value }))

  const handleSave = async () => {
    setError(null)
    try {
      const payload = {
        detection_line_y_percent: parseInt(form.detection_line_y_percent),
        min_contour_area: parseInt(form.min_contour_area),
        count_cooldown_ms: parseInt(form.count_cooldown_ms),
        conveyor_visible_feet: parseFloat(form.conveyor_visible_feet),
        downtime_threshold_seconds: parseInt(form.downtime_threshold_seconds),
        target_pieces_per_hour: parseInt(form.target_pieces_per_hour),
        shift_day_start: form.shift_day_start,
        shift_aft_start: form.shift_aft_start,
        shift_night_start: form.shift_night_start,
      }
      const res = await fetch(`${API}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await res.text())
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleReset = async () => {
    if (!resetConfirm) {
      setResetConfirm(true)
      return
    }
    try {
      const res = await fetch(`${API}/api/metrics/pieces/reset`, { method: 'POST' })
      const data = await res.json()
      setResetMsg(`Cleared ${data.deleted} piece records.`)
      setTimeout(() => setResetMsg(null), 4000)
    } catch (e) {
      setResetMsg('Reset failed — check API connection.')
      setTimeout(() => setResetMsg(null), 4000)
    } finally {
      setResetConfirm(false)
    }
  }

  const handleCalibrate = async () => {
    try {
      const res = await fetch(`${API}/api/calibrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conveyor_visible_feet: parseFloat(form.conveyor_visible_feet) }),
      })
      if (res.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (_) {}
  }

  return (
    <div className="p-5 max-w-2xl mx-auto flex flex-col gap-4 pb-12">
      <div className="pt-2 pb-1">
        <h1 className="text-[22px] font-bold text-white tracking-tight">Settings</h1>
      </div>

      <Section title="Camera">
        <Field
          label="RTSP URL"
          name="camera_rtsp_url"
          value={form.camera_rtsp_url}
          onChange={set}
          hint="rtsp://admin:PASSWORD@IP:554/Streaming/Channels/101 (Hikvision format)"
        />
        <div className="flex gap-3">
          <button
            onClick={() => setTesting(t => !t)}
            className="px-4 py-2 text-[13px] rounded-xl transition-colors"
            style={{
              border: '1px solid rgba(84,84,88,0.6)',
              color: 'rgba(235,235,245,0.55)',
            }}
          >
            {testing ? 'Close Preview' : 'Test Camera'}
          </button>
        </div>
        {testing && (
          <div className="bg-black rounded-xl overflow-hidden">
            <img
              src={`http://${window.location.hostname}:8080/debug_feed`}
              alt="Camera preview"
              className="w-full"
              onError={() => {}}
            />
          </div>
        )}
      </Section>

      <Section title="Detection Tuning">
        <RangeField
          label="Detection Line Position"
          name="detection_line_y_percent"
          value={form.detection_line_y_percent}
          onChange={set}
          min={5} max={95} unit="%"
          hint="Vertical position of the counting tripwire (% from top). Enable debug feed to visualize."
        />
        <RangeField
          label="Min Contour Area"
          name="min_contour_area"
          value={form.min_contour_area}
          onChange={set}
          min={500} max={20000} step={100} unit=" px²"
          hint="Minimum moving region to count as a board. Increase to filter dust and noise."
        />
        <RangeField
          label="Count Cooldown"
          name="count_cooldown_ms"
          value={form.count_cooldown_ms}
          onChange={set}
          min={200} max={3000} step={50} unit=" ms"
          hint="Minimum time between counts. Prevents double-counting a slow board."
        />
      </Section>

      <Section title="Speed Calibration">
        <Field
          label="Conveyor Visible Length (feet)"
          name="conveyor_visible_feet"
          value={form.conveyor_visible_feet}
          onChange={set}
          type="number"
          min="1"
          step="0.5"
          hint="Real-world length of conveyor visible in the camera frame. Used to convert pixel velocity to FPM."
        />
        <button
          onClick={handleCalibrate}
          className="self-start px-4 py-2 text-[13px] rounded-xl font-medium transition-colors"
          style={{ background: 'rgba(10,132,255,0.15)', color: '#0A84FF', border: '1px solid rgba(10,132,255,0.3)' }}
        >
          Save Calibration
        </button>
      </Section>

      <Section title="Downtime & Production Targets">
        <RangeField
          label="Downtime Threshold"
          name="downtime_threshold_seconds"
          value={form.downtime_threshold_seconds}
          onChange={set}
          min={10} max={300} step={5} unit=" s"
          hint="Seconds with no board detection before declaring downtime."
        />
        <Field
          label="Target Pieces Per Hour"
          name="target_pieces_per_hour"
          value={form.target_pieces_per_hour}
          onChange={set}
          type="number"
          min="1"
        />
      </Section>

      <Section title="Shift Schedule">
        <div className="grid grid-cols-3 gap-4">
          <Field label="Day Shift" name="shift_day_start" value={form.shift_day_start} onChange={set} hint="HH:MM" />
          <Field label="Afternoon Shift" name="shift_aft_start" value={form.shift_aft_start} onChange={set} hint="HH:MM" />
          <Field label="Night Shift" name="shift_night_start" value={form.shift_night_start} onChange={set} hint="HH:MM" />
        </div>
      </Section>

      <Section title="Operations">
        <div className="flex flex-col gap-3">
          <div className="text-[12px] text-[rgba(235,235,245,0.35)]">
            Deletes all piece events recorded today. Use at shift start or after a calibration run.
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleReset}
              className="px-4 py-2 text-[13px] rounded-xl font-medium transition-colors"
              style={
                resetConfirm
                  ? { background: 'rgba(255,69,58,0.12)', color: '#FF453A', border: '1px solid rgba(255,69,58,0.35)' }
                  : { background: 'transparent', color: 'rgba(235,235,245,0.5)', border: '1px solid rgba(84,84,88,0.6)' }
              }
            >
              {resetConfirm ? 'Confirm Reset?' : 'Reset Piece Count'}
            </button>
            {resetConfirm && (
              <button
                onClick={() => setResetConfirm(false)}
                className="text-[13px] text-[rgba(235,235,245,0.35)] hover:text-white transition-colors"
              >
                Cancel
              </button>
            )}
            {resetMsg && (
              <span className="text-[13px] text-[#30D158]">{resetMsg}</span>
            )}
          </div>
        </div>
      </Section>

      {/* Save */}
      <div className="flex items-center gap-4 pt-1">
        <button
          onClick={handleSave}
          className="px-6 py-2.5 text-[13px] font-semibold rounded-xl transition-colors"
          style={{ background: '#0A84FF', color: '#fff' }}
          onMouseEnter={e => e.currentTarget.style.background = '#409CFF'}
          onMouseLeave={e => e.currentTarget.style.background = '#0A84FF'}
        >
          Save Settings
        </button>
        {saved && <span className="text-[13px] text-[#30D158] font-medium">Saved.</span>}
        {error && <span className="text-[13px] text-[#FF453A]">{error}</span>}
      </div>
    </div>
  )
}
