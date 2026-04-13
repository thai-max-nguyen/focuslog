import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { TrendingUp } from 'lucide-react'
import { API, CATEGORY_COLORS, fmtDuration } from '../App'

type WeekDay = {
  date: string; day: string; total_active: number; deep_work: number
  distractions: number; productivity_score: number
  top_apps: { app_name: string; duration: number }[]
  categories: Record<string, number>
}

export default function Trends({ refreshKey }: { refreshKey: number }) {
  const [week, setWeek] = useState<WeekDay[]>([])
  useEffect(() => {
    fetch(`${API}/api/weekly`).then(r => r.json()).then(setWeek).catch(() => {})
  }, [refreshKey])

  const avgDeepWork = week.length ? Math.round(week.reduce((a, d) => a + d.deep_work, 0) / week.length) : 0
  const totalFocus = week.reduce((a, d) => a + d.total_active, 0)
  const appMap: Record<string, number> = {}
  week.forEach(d => d.top_apps.forEach(a => { appMap[a.app_name] = (appMap[a.app_name] ?? 0) + a.duration }))
  const topAppName = Object.entries(appMap).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—'
  const topAppTime = appMap[topAppName] ?? 0
  const catTotals: Record<string, number> = {}
  week.forEach(d => Object.entries(d.categories).forEach(([k, v]) => { catTotals[k] = (catTotals[k] ?? 0) + v }))
  const catTotal = Object.values(catTotals).reduce((a, b) => a + b, 0)
  const today = new Date().toISOString().slice(0, 10)

  return (
    <div>
      <h1 style={{ fontSize: 32, fontWeight: 700, color: '#e5e2e1', letterSpacing: '-0.02em', marginBottom: 24 }}>Weekly Productivity Trends</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'AVG. DEEP WORK/DAY', value: fmtDuration(avgDeepWork), accent: '#e5e2e1', sub: undefined },
          { label: 'TOP PRODUCTIVE APP', value: topAppName, sub: `${fmtDuration(topAppTime)} active usage`, accent: '#4ecdc4' },
          { label: 'TOTAL FOCUS TIME', value: `${(totalFocus / 3600).toFixed(1)}h`, accent: '#f7c948', sub: undefined },
        ].map(card => (
          <div key={card.label} style={{ background: '#201f1f', borderRadius: 12, padding: 24, borderTop: `2px solid ${card.accent}33` }}>
            <div style={{ fontSize: 10, color: '#6b6b6b', letterSpacing: '0.1em', marginBottom: 12 }}>{card.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: card.accent, letterSpacing: '-0.02em' }}>{card.value}</div>
            {card.sub && <div style={{ fontSize: 12, color: '#555', marginTop: 6 }}>{card.sub}</div>}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        <div style={{ background: '#201f1f', borderRadius: 12, padding: 24 }}>
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e5e2e1', marginBottom: 4 }}>Weekly Productivity Intensity</div>
            <div style={{ fontSize: 12, color: '#555' }}>Aggregated focus scores across all categories</div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={week.map(d => ({ ...d, isToday: d.date === today }))} barSize={36}>
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#555', fontSize: 12 }} />
              <YAxis hide />
              <Tooltip content={({ active, payload }) => {
                if (!active || !payload?.[0]) return null
                const d = payload[0].payload as WeekDay & { isToday: boolean }
                return (
                  <div style={{ background: 'rgba(32,31,31,0.95)', backdropFilter: 'blur(24px)', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#e5e2e1' }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.date}</div>
                    <div style={{ color: '#6b6b6b' }}>Active: {fmtDuration(d.total_active)}</div>
                    <div style={{ color: '#4f86f7' }}>Deep work: {fmtDuration(d.deep_work)}</div>
                    <div style={{ color: '#ff6b6b' }}>Score: {Math.round(d.productivity_score * 100)}%</div>
                  </div>
                )
              }} />
              <Bar dataKey="deep_work" radius={[4, 4, 0, 0]}>
                {week.map((d, i) => (
                  <Cell key={i} fill={d.date === today ? '#568dfe' : d.deep_work > avgDeepWork ? '#4f86f7' : '#2a2a2a'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 11 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#555' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#568dfe', display: 'inline-block' }} /> HIGH PERFORMANCE</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#555' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#2a2a2a', border: '1px solid #444', display: 'inline-block' }} /> BASELINE</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ background: '#201f1f', borderRadius: 12, padding: 24, flex: 1 }}>
            <div style={{ fontSize: 11, color: '#555', letterSpacing: '0.1em', marginBottom: 16 }}>ACTIVITY MIX</div>
            {Object.entries(catTotals).sort((a, b) => b[1] - a[1]).map(([cat, secs]) => {
              const pct = catTotal > 0 ? Math.round((secs / catTotal) * 100) : 0
              const color = CATEGORY_COLORS[cat] ?? '#555'
              return (
                <div key={cat} style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 13 }}>
                    <span style={{ color: '#aaa' }}>{cat}</span>
                    <span style={{ color: '#e5e2e1', fontWeight: 600 }}>{pct}%</span>
                  </div>
                  <div style={{ height: 3, background: '#131313', borderRadius: 2 }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 2 }} />
                  </div>
                </div>
              )
            })}
            {catTotal === 0 && <div style={{ color: '#555', fontSize: 12 }}>No data this week</div>}
          </div>
          <div style={{ background: '#201f1f', borderRadius: 12, padding: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <TrendingUp size={16} color="#b0c6ff" />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#e5e2e1' }}>Observer Insights</span>
            </div>
            <p style={{ fontSize: 12, color: '#6b6b6b', lineHeight: 1.7 }}>
              {totalFocus > 0
                ? `Your most active day was ${week.reduce((a, b) => a.total_active > b.total_active ? a : b, week[0])?.day ?? '—'}. Deep work is ${catTotal > 0 ? Math.round(((catTotals['Work'] ?? 0) / catTotal) * 100) : 0}% of total tracked time this week.`
                : 'Start tracking to see personalized insights about your productivity patterns.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
