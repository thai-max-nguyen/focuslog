import { format, addDays, subDays, parseISO } from 'date-fns'

type Props = {
  date: string
  onDateChange: (d: string) => void
}

const btn: React.CSSProperties = {
  background: '#2a2a2a',
  border: '1px solid #333',
  color: '#e8e8e8',
  borderRadius: 6,
  padding: '6px 10px',
  cursor: 'pointer',
  fontSize: 14,
}

export default function Header({ date, onDateChange }: Props) {
  const d = parseISO(date)
  const isToday = date === format(new Date(), 'yyyy-MM-dd')

  return (
    <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 22, fontWeight: 700 }}>⏱ FocusLog</span>
        <span style={{ fontSize: 11, color: '#444', background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 4, padding: '2px 7px' }}>local · private</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button style={btn} onClick={() => onDateChange(format(subDays(d, 1), 'yyyy-MM-dd'))}>‹</button>
        <span style={{ minWidth: 130, textAlign: 'center', fontWeight: 500 }}>
          {isToday ? 'Today' : format(d, 'MMM d, yyyy')}
        </span>
        <button style={{ ...btn, opacity: isToday ? 0.4 : 1 }} disabled={isToday}
          onClick={() => onDateChange(format(addDays(d, 1), 'yyyy-MM-dd'))}>›</button>
        <a href={`http://127.0.0.1:7331/api/export?date=${date}&fmt=csv`}
          style={{ ...btn, textDecoration: 'none', padding: '6px 12px', fontSize: 12, color: '#aaa' }}>
          Export CSV
        </a>
      </div>
    </header>
  )
}
