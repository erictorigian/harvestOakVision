import { useState, useEffect } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function Field({ label, name, value, onChange, type = 'text', min, max, step, hint }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[10px] font-mono tracking-[0.15em] text-[#8B949E] uppercase">
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
        className="bg-surface border border-border rounded px-3 py-2 text-sm font-mono text-[#E6EDF3] focus:outline-none focus:border-amber/50 w-full"
      />
      {hint && <div className="text-[10px] text-[#484F58] font-mono">{hint}</div>}
    </div>
  )
}

function RangeField({ label, name, value, onChange, min, max, step = 1, unit, hint }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-center">
        <label className="text-[10px] font-mono tracking-[0.15em] text-[#8B949E] uppercase">{label}</label>
        <span className="text-xs font-mono text-amber">{value}{unit}</span>
      </div>
      <input
        type="range"
        name={name}
        value={value}
        onChange={e => onChange(name, e.target.value)}
        min={min}
        max={max}
        step={step}
        className="w-full accent-amber"
      />
      {hint && <div className="text-[10px] text-[#484F58] font-mono">{hint}</div>}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="bg-panel border border-border rounded-lg p-5">
      <div className="text-[10px] font-mono tracking-[0.2em] text-[#8B949E] uppercase mb-4">
        {title}
      </div>
      <div className="flex flex-col gap-4">
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
    <div className="p-5 max-w-3xl mx-auto flex flex-col gap-5">
      <div className="font-mono text-sm text-[#E6EDF3] tracking-wider">SETTINGS</div>

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
            className="px-4 py-2 text-xs font-mono tracking-wider border border-border rounded hover:border-amber/40 hover:text-amber transition-colors text-[#8B949E]"
          >
            {testing ? 'CLOSE PREVIEW' : 'TEST CAMERA'}
          </button>
        </div>
        {testing && (
          <div className="bg-black rounded overflow-hidden">
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
          min={500} max={20000} step={100} unit="px²"
          hint="Minimum moving region size to count as a board. Increase to reduce dust/noise false positives."
        />
        <RangeField
          label="Count Cooldown"
          name="count_cooldown_ms"
          value={form.count_cooldown_ms}
          onChange={set}
          min={200} max={3000} step={50} unit="ms"
          hint="Minimum time between counts on the same zone. Prevents double-counting a slow board."
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
          hint="Measure the real-world length of conveyor visible in the camera frame. Used to convert pixel velocity to FPM."
        />
        <button
          onClick={handleCalibrate}
          className="self-start px-4 py-2 text-xs font-mono tracking-wider border border-amber/40 text-amber rounded hover:bg-amber/10 transition-colors"
        >
          SAVE CALIBRATION
        </button>
      </Section>

      <Section title="Downtime & Production Targets">
        <RangeField
          label="Downtime Threshold"
          name="downtime_threshold_seconds"
          value={form.downtime_threshold_seconds}
          onChange={set}
          min={10} max={300} step={5} unit="s"
          hint="Seconds of no board detection before declaring downtime."
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
          <Field label="Day Shift Start" name="shift_day_start" value={form.shift_day_start} onChange={set} />
          <Field label="Afternoon Shift" name="shift_aft_start" value={form.shift_aft_start} onChange={set} />
          <Field label="Night Shift" name="shift_night_start" value={form.shift_night_start} onChange={set} />
        </div>
        <div className="text-[10px] font-mono text-[#484F58]">24-hour format HH:MM</div>
      </Section>

      <Section title="Operations">
        <div className="flex flex-col gap-2">
          <div className="text-[10px] font-mono text-[#484F58]">
            Deletes all piece_events recorded today. Use at shift start or after a calibration run.
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleReset}
              className={`px-4 py-2 text-xs font-mono tracking-wider rounded border transition-colors ${
                resetConfirm
                  ? 'border-red-500 text-red-400 bg-red-500/10 hover:bg-red-500/20'
                  : 'border-border text-[#8B949E] hover:border-red-500/40 hover:text-red-400'
              }`}
            >
              {resetConfirm ? 'CONFIRM RESET?' : 'RESET PIECE COUNT'}
            </button>
            {resetConfirm && (
              <button
                onClick={() => setResetConfirm(false)}
                className="text-xs font-mono text-[#484F58] hover:text-[#8B949E] transition-colors"
              >
                cancel
              </button>
            )}
            {resetMsg && (
              <span className="text-xs font-mono text-emerald-400">{resetMsg}</span>
            )}
          </div>
        </div>
      </Section>

      {/* Save button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          className="px-6 py-2.5 bg-amber/20 border border-amber/50 text-amber font-mono text-xs tracking-widest rounded hover:bg-amber/30 transition-colors"
        >
          SAVE SETTINGS
        </button>
        {saved && (
          <span className="text-emerald-400 font-mono text-xs">Settings saved.</span>
        )}
        {error && (
          <span className="text-red-400 font-mono text-xs">{error}</span>
        )}
      </div>
    </div>
  )
}
