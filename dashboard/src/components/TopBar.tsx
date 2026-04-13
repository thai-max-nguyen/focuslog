import { format, addDays, subDays, parseISO } from 'date-fns'
import { API } from '../App'

export default function TopBar({ date, onDateChange }: { date: string; onDateChange: (d: string) => void }) {
  const d = parseISO(date)
  const isToday = date === format(new Date(), 'yyyy-MM-dd')
  const label = isToday ? 'Today' : format(d, 'MMM d, yyyy')

  return (
    <div style={{ padding: '16px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#131313', borderBottom: '1px solid #1a1a1a' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button onClick={() => onDateChange(format(subDays(d, 1), 'yyyy-MM-dd'))} style={ghostBtn}>‹</button>
        <span style={{ fontSize: 14, fontWeight: 500, color: '#e5e2e1', minWidth: 90, textAlign: 'center' }}>{label}</span>
        <button onClick={() => onDateChange(format(addDays(d, 1), 'yyyy-MM-dd'))} disabled={isToday} style={{ ...ghostBtn, opacity: isToday ? 0.3 : 1 }}>›</button>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
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
