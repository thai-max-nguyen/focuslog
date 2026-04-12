import { useEffect, useState } from 'react'
import { fetchTimeline } from '../App'
import type { Session } from '../App'

const COLORS: Record<string, string> = {
  Work: '#4f86f7',
  Communication: '#f7c948',
  Learning: '#4ecdc4',
  Entertainment: '#ff6b6b',
  Unknown: '#444',
}

const DAY = 86400

function fmt(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function Timeline({ date }: { date: string }) {
  const [blocks, setBlocks] = useState<Session[]>([])
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    setError(false)
    fetchTimeline(date).then(setBlocks).catch(() => setError(true))
  }, [date])

  if (error) return (
    <div className="card">
      <h2>Timeline</h2>
      <p style={{ color: '#555', padding: '24px 0', textAlign: 'center' }}>
        FocusLog daemon not running. Start it with <code style={{ color: '#4f86f7' }}>python -m tracker.main</code>
      </p>
    </div>
  )

  if (blocks.length === 0) return (
    <div className="card">
      <h2>Timeline — {date}</h2>
      <p style={{ color: '#555', padding: '24px 0', textAlign: 'center' }}>No activity recorded for this day.</p>
    </div>
  )

  const dayStart = Math.floor(blocks[0].start_time / DAY) * DAY

  return (
    <div className="card">
      <h2>Timeline — {date}</h2>
      <div style={{ position: 'relative', height: 44, background: '#111', borderRadius: 8, overflow: 'hidden' }}>
        {blocks.map((b, i) => {
          const left = ((b.start_time - dayStart) / DAY) * 100
          const width = Math.max((b.duration / DAY) * 100, 0.15)
          return (
            <div key={i}
              onMouseEnter={(e) => setTooltip({ text: `${b.app_name} · ${b.category} · ${fmt(b.duration)}`, x: e.clientX, y: e.clientY })}
              onMouseLeave={() => setTooltip(null)}
              style={{
                position: 'absolute', left: `${left}%`, width: `${width}%`,
                top: 0, height: '100%',
                background: COLORS[b.category] ?? COLORS.Unknown,
                opacity: 0.85, cursor: 'default',
              }}
            />
          )
        })}
      </div>
      {tooltip && (
        <div style={{
          position: 'fixed', left: tooltip.x + 10, top: tooltip.y - 30,
          background: '#222', border: '1px solid #333', borderRadius: 6,
          padding: '5px 10px', fontSize: 12, pointerEvents: 'none', zIndex: 999,
        }}>{tooltip.text}</div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 11, color: '#444' }}>
        {['12am','3am','6am','9am','12pm','3pm','6pm','9pm',''].map((t, i) => <span key={i}>{t}</span>)}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 12 }}>
        {Object.entries(COLORS).map(([cat, color]) => (
          <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
            <span style={{ color: '#666' }}>{cat}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
