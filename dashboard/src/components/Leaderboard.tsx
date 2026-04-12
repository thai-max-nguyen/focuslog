import { useEffect, useState } from 'react'
import { fetchSummary } from '../App'

function fmt(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function Leaderboard({ date }: { date: string }) {
  const [apps, setApps] = useState<{ app_name: string; duration: number }[]>([])
  const [total, setTotal] = useState(0)

  useEffect(() => {
    fetchSummary(date).then((s) => {
      setApps(s.top_apps)
      setTotal(s.total_active)
    }).catch(console.error)
  }, [date])

  return (
    <div className="card">
      <h2>Top Apps</h2>
      {apps.length === 0
        ? <p style={{ color: '#555' }}>No data for this day.</p>
        : apps.slice(0, 8).map((app, i) => {
            const pct = total > 0 ? (app.duration / total) * 100 : 0
            return (
              <div key={app.app_name} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
                  <span style={{ color: '#ccc' }}>{i + 1}. {app.app_name}</span>
                  <span style={{ color: '#555' }}>{fmt(app.duration)}</span>
                </div>
                <div style={{ height: 3, background: '#222', borderRadius: 2 }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: '#4f86f7', borderRadius: 2, transition: 'width 0.4s ease' }} />
                </div>
              </div>
            )
          })
      }
    </div>
  )
}
