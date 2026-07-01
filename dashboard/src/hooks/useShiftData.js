import { useState, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useHourlyData(dateStr) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  const fetch_ = useCallback(async () => {
    try {
      const url = dateStr
        ? `${API}/api/metrics/hourly?date=${dateStr}`
        : `${API}/api/metrics/hourly`
      const res = await fetch(url)
      if (res.ok) setData(await res.json())
    } catch (_) {}
    finally { setLoading(false) }
  }, [dateStr])

  useEffect(() => {
    fetch_()
    const t = setInterval(fetch_, 60_000)
    return () => clearInterval(t)
  }, [fetch_])

  return { data, loading }
}

export function useShifts() {
  const [shifts, setShifts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/api/shifts`)
      .then(r => r.json())
      .then(setShifts)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { shifts, loading }
}

export function useDowntimeEvents(dateStr) {
  const [events, setEvents] = useState([])

  const fetch_ = useCallback(async () => {
    try {
      const url = dateStr
        ? `${API}/api/downtime?date=${dateStr}`
        : `${API}/api/downtime`
      const res = await fetch(url)
      if (res.ok) setEvents(await res.json())
    } catch (_) {}
  }, [dateStr])

  useEffect(() => {
    fetch_()
    const t = setInterval(fetch_, 30_000)
    return () => clearInterval(t)
  }, [fetch_])

  return events
}

export function useTodaySummary() {
  const [summary, setSummary] = useState(null)

  useEffect(() => {
    const fetch_ = () =>
      fetch(`${API}/api/metrics/today`)
        .then(r => r.json())
        .then(setSummary)
        .catch(() => {})
    fetch_()
    const t = setInterval(fetch_, 30_000)
    return () => clearInterval(t)
  }, [])

  return summary
}
