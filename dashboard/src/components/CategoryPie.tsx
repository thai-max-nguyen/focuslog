import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchSummary } from '../App'
import type { Summary } from '../App'

const COLORS: Record<string, string> = {
  Work: '#4f86f7',
  Communication: '#f7c948',
  Learning: '#4ecdc4',
  Entertainment: '#ff6b6b',
  Unknown: '#444',
}

function fmt(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function CategoryPie({ date }: { date: string }) {
  const [summary, setSummary] = useState<Summary | null>(null)

  useEffect(() => {
    fetchSummary(date).then(setSummary).catch(console.error)
  }, [date])

  if (!summary) return <div className="card"><h2>Categories</h2><p style={{ color: '#555' }}>Loading...</p></div>

  const data = Object.entries(summary.categories).map(([name, value]) => ({ name, value }))
  const score = Math.round(summary.productivity_score * 100)
  const scoreColor = score >= 60 ? '#4ecdc4' : score >= 30 ? '#f7c948' : '#ff6b6b'

  return (
    <div className="card">
      <h2>Categories</h2>
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        <ResponsiveContainer width={160} height={160}>
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={42} outerRadius={68} dataKey="value">
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name] ?? '#444'} />
              ))}
            </Pie>
            <Tooltip formatter={(v) => fmt(Number(v))} contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 6 }} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ flex: 1, paddingTop: 8 }}>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: '#555', marginBottom: 4 }}>Productivity Score</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: scoreColor }}>{score}%</div>
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.8, color: '#666' }}>
            <div>Active: <span style={{ color: '#aaa' }}>{fmt(summary.total_active)}</span></div>
            <div>Deep work: <span style={{ color: '#aaa' }}>{fmt(summary.deep_work)}</span></div>
            <div>Distractions: <span style={{ color: '#aaa' }}>{summary.distractions}</span></div>
          </div>
        </div>
      </div>
    </div>
  )
}
