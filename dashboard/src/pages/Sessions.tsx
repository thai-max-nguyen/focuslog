import { useEffect, useState } from 'react'
import { Search, Tag } from 'lucide-react'
import { API, type SessionWithTag, CATEGORY_COLORS, AppIcon, CategoryIcon, fmtDuration, fmtTime } from '../App'
import { isBrowserApp, parseBrowserTitle } from '../utils'

const CATEGORIES = ['All Categories', 'Work', 'Communication', 'Learning', 'Entertainment', 'Unknown']
const MIN_TAGGABLE_DURATION_SECS = 3 * 60

function TaskPill({ session }: { session: SessionWithTag }) {
  if (session.task_label) {
    const isInferred = session.task_source === 'inferred' || session.task_source === 'inferred_category'
    return (
      <span style={{
        fontSize: 11, padding: '3px 9px', borderRadius: 12,
        background: isInferred ? '#1a1a1a' : '#1e2a3a',
        color: isInferred ? '#666' : '#4f86f7',
        border: `1px solid ${isInferred ? '#252525' : '#2a3a5a'}`,
        fontStyle: isInferred ? 'italic' : 'normal',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        maxWidth: 140,
      }}>
        {isInferred ? `~${session.task_label}` : session.task_label}
      </span>
    )
  }
  if ((session.duration ?? 0) >= MIN_TAGGABLE_DURATION_SECS) {
    return (
      <button
        onClick={() => {
          const w = window.open(`${API}/tag?session_id=${session.id}`, '_blank', 'width=390,height=320')
          if (!w) window.location.href = `${API}/tag?session_id=${session.id}`
        }}
        style={{
          background: 'none', border: '1px solid #2a2a2a', borderRadius: 12,
          color: '#555', fontSize: 11, cursor: 'pointer', padding: '3px 9px',
          display: 'flex', alignItems: 'center', gap: 4,
        }}
      >
        <Tag size={9} />＋ Tag
      </button>
    )
  }
  return <span style={{ color: '#333', fontSize: 11 }}>—</span>
}

export default function Sessions({ date, refreshKey }: { date: string; refreshKey: number }) {
  const [sessions, setSessions] = useState<SessionWithTag[]>([])
  const [search, setSearch] = useState('')
  const [cat, setCat] = useState('All Categories')
  const [filterUntagged, setFilterUntagged] = useState(false)
  const totalActive = sessions.reduce((a, s) => a + s.duration, 0)

  useEffect(() => {
    fetch(`${API}/api/sessions?date=${date}`)
      .then(r => r.json())
      .then((data: SessionWithTag[]) => setSessions(data))
      .catch(() => {})
  }, [date, refreshKey])

  const filtered = sessions.filter(s => {
    if (cat !== 'All Categories' && s.category !== cat) return false
    if (filterUntagged && s.task_label) return false
    if (search && !s.app_name.toLowerCase().includes(search.toLowerCase()) &&
        !(s.window_title ?? '').toLowerCase().includes(search.toLowerCase())) return false
    return true
  }).reverse()

  const hh = String(Math.floor(totalActive / 3600)).padStart(2, '0')
  const mm = String(Math.floor((totalActive % 3600) / 60)).padStart(2, '0')
  const ss = String(totalActive % 60).padStart(2, '0')

  const untaggedCount = sessions.filter(s => !s.task_label && (s.duration ?? 0) >= MIN_TAGGABLE_DURATION_SECS).length

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 32, fontWeight: 700, color: '#e5e2e1', letterSpacing: '-0.02em', marginBottom: 6 }}>Raw Sessions Log</h1>
          <p style={{ fontSize: 13, color: '#6b6b6b', lineHeight: 1.5 }}>
            Detailed granular view of all application activity captured by the observer.<br />
            Every context switch is accounted for.
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 10, color: '#568dfe', letterSpacing: '0.1em', marginBottom: 4 }}>ACTIVE TIME</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: '#e5e2e1', letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
            {hh}:{mm}:{ss}
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'center' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#555' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Filter by App Name..."
            style={{ width: '100%', background: '#0e0e0e', border: 'none', borderRadius: 8, padding: '10px 12px 10px 34px', color: '#e5e2e1', fontSize: 13, outline: 'none' }} />
        </div>
        <select value={cat} onChange={e => setCat(e.target.value)}
          style={{ background: '#0e0e0e', border: 'none', borderRadius: 8, padding: '10px 16px', color: cat === 'All Categories' ? '#6b6b6b' : '#e5e2e1', fontSize: 13, cursor: 'pointer', outline: 'none' }}>
          {CATEGORIES.map(c => <option key={c}>{c}</option>)}
        </select>
        {untaggedCount > 0 && (
          <button
            onClick={() => setFilterUntagged(f => !f)}
            style={{
              background: filterUntagged ? '#1e2a3a' : '#0e0e0e', border: 'none', borderRadius: 8,
              padding: '10px 14px', color: filterUntagged ? '#4f86f7' : '#555',
              fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {untaggedCount} untagged
          </button>
        )}
      </div>

      {/* Table header */}
      <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 140px 110px 90px 150px', gap: 12, padding: '8px 16px 8px 20px', fontSize: 11, color: '#555', letterSpacing: '0.08em', marginBottom: 4 }}>
        <span>APP NAME</span><span>WINDOW TITLE</span><span>CATEGORY</span><span>START TIME</span><span style={{ textAlign: 'right' }}>DURATION</span><span>TASK</span>
      </div>

      {/* Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {filtered.map(s => {
          const color = CATEGORY_COLORS[s.category] ?? '#555'
          return (
            <div key={s.id} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 140px 110px 90px 150px', gap: 12, alignItems: 'center', background: '#201f1f', borderRadius: 10, padding: '12px 16px', borderLeft: `4px solid ${color}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                <AppIcon name={s.app_name} windowTitle={s.window_title ?? undefined} size={26} />
                <span style={{ fontSize: 13, fontWeight: 500, color: '#e5e2e1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.app_name}</span>
              </div>
              <span style={{ fontSize: 12, color: '#6b6b6b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {isBrowserApp(s.app_name) && s.window_title ? parseBrowserTitle(s.window_title).cleanTitle || s.window_title : s.window_title || '—'}
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: 20, background: color + '22', color, fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', whiteSpace: 'nowrap' }}>
                <CategoryIcon category={s.category} size={10} />
                {s.category.toUpperCase()}
              </span>
              <span style={{ fontSize: 12, color: '#6b6b6b', fontVariantNumeric: 'tabular-nums' }}>{fmtTime(s.start_time)}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#e5e2e1', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{fmtDuration(s.duration)}</span>
              <TaskPill session={s} />
            </div>
          )
        })}
        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#555', fontSize: 13 }}>No sessions found</div>
        )}
      </div>
    </div>
  )
}
