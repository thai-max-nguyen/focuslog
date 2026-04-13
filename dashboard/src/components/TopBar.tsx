import { useEffect, useRef, useState } from 'react'
import { format, addDays, subDays, parseISO } from 'date-fns'
import { RefreshCw } from 'lucide-react'
import { API } from '../App'

const INTERVALS = [
  { label: 'Off', value: 0 },
  { label: '10s', value: 10 },
  { label: '30s', value: 30 },
  { label: '60s', value: 60 },
]

export default function TopBar({ date, onDateChange, onRefresh }: {
  date: string
  onDateChange: (d: string) => void
  onRefresh: () => void
}) {
  const d = parseISO(date)
  const isToday = date === format(new Date(), 'yyyy-MM-dd')
  const label = isToday ? 'Today' : format(d, 'MMM d, yyyy')
  const [intervalSecs, setIntervalSecs] = useState(0)
  const [spinning, setSpinning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const spinTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onRefreshRef = useRef(onRefresh)
  onRefreshRef.current = onRefresh

  const triggerRefresh = () => {
    if (spinTimerRef.current) clearTimeout(spinTimerRef.current)
    setSpinning(true)
    onRefreshRef.current()
    spinTimerRef.current = setTimeout(() => setSpinning(false), 600)
  }

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (intervalSecs > 0) {
      intervalRef.current = setInterval(triggerRefresh, intervalSecs * 1000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (spinTimerRef.current) clearTimeout(spinTimerRef.current)
    }
  }, [intervalSecs])

  return (
    <div style={{ padding: '16px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#131313', borderBottom: '1px solid #1a1a1a' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button onClick={() => onDateChange(format(subDays(d, 1), 'yyyy-MM-dd'))} style={ghostBtn}>‹</button>
        <span style={{ fontSize: 14, fontWeight: 500, color: '#e5e2e1', minWidth: 90, textAlign: 'center' }}>{label}</span>
        <button onClick={() => onDateChange(format(addDays(d, 1), 'yyyy-MM-dd'))} disabled={isToday} style={{ ...ghostBtn, opacity: isToday ? 0.3 : 1 }}>›</button>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#0e0e0e', borderRadius: 8, padding: '4px 4px 4px 10px' }}>
          {intervalSecs > 0 && (
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ecdc4', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
          )}
          <span style={{ fontSize: 11, color: '#555', letterSpacing: '0.06em' }}>AUTO</span>
          <select
            value={intervalSecs}
            onChange={e => setIntervalSecs(Number(e.target.value))}
            style={{ background: 'transparent', border: 'none', color: '#e5e2e1', fontSize: 11, cursor: 'pointer', outline: 'none', padding: '4px 6px' }}
          >
            {INTERVALS.map(i => <option key={i.value} value={i.value}>{i.label}</option>)}
          </select>
        </div>
        <button
          onClick={triggerRefresh}
          title="Refresh data"
          style={{ ...ghostBtn, display: 'flex', alignItems: 'center', gap: 6, padding: '7px 12px', background: '#0e0e0e', borderRadius: 8 }}
        >
          <RefreshCw size={13} style={{ transition: 'transform 0.6s', transform: spinning ? 'rotate(360deg)' : 'rotate(0deg)', color: '#568dfe' }} />
          <span style={{ fontSize: 11, color: '#e5e2e1', letterSpacing: '0.04em' }}>Refresh</span>
        </button>
        <span style={{ fontSize: 11, color: '#555' }}>local · private</span>
        <a href={`${API}/api/export?date=${date}&fmt=csv`} style={{ background: 'linear-gradient(135deg, #b0c6ff, #568dfe)', color: '#fff', padding: '7px 16px', borderRadius: 6, fontSize: 12, fontWeight: 600, textDecoration: 'none', letterSpacing: '0.02em', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.1)' }}>
          Export CSV
        </a>
      </div>
    </div>
  )
}

const ghostBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', color: '#e5e2e1', cursor: 'pointer',
  fontSize: 18, padding: '4px 8px', borderRadius: 4,
}
