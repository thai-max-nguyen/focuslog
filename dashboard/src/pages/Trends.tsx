import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line } from 'recharts'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { API, CATEGORY_COLORS, fmtDuration } from '../App'

type WeekDay = {
  date: string; day: string; total_active: number; deep_work: number
  distractions: number; productivity_score: number
  top_apps: { app_name: string; duration: number }[]
  categories: Record<string, number>
  longest_session: number; longest_session_app: string
  peak_hour: number; switch_rate: number
  focus_efficiency: number; worst_distraction_app: string
}

function fmtHour(h: number): string {
  if (h < 0) return '—'
  if (h === 0) return '12am'
  if (h < 12) return `${h}am`
  if (h === 12) return '12pm'
  return `${h - 12}pm`
}

export default function Trends({ refreshKey }: { refreshKey: number }) {
  const [week, setWeek] = useState<WeekDay[]>([])
  useEffect(() => {
    fetch(`${API}/api/weekly`).then(r => r.json()).then(setWeek).catch(() => {})
  }, [refreshKey])

  const activeDays = week.filter(d => d.total_active > 0)
  const avgDeepWork = activeDays.length ? Math.round(activeDays.reduce((a, d) => a + d.deep_work, 0) / activeDays.length) : 0
  const totalFocus = week.reduce((a, d) => a + d.total_active, 0)

  const appMap: Record<string, number> = {}
  week.forEach(d => d.top_apps.forEach(a => { appMap[a.app_name] = (appMap[a.app_name] ?? 0) + a.duration }))
  const topAppName = Object.entries(appMap).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—'
  const topAppTime = appMap[topAppName] ?? 0

  const catTotals: Record<string, number> = {}
  week.forEach(d => Object.entries(d.categories).forEach(([k, v]) => {
    if (k !== 'Unknown' && k !== 'Idle') catTotals[k] = (catTotals[k] ?? 0) + v
  }))
  const catTotal = Object.values(catTotals).reduce((a, b) => a + b, 0)

  const today = new Date().toISOString().slice(0, 10)

  // Trend direction: compare first half vs second half of the week
  const half = Math.floor(activeDays.length / 2)
  const firstHalf = activeDays.slice(0, half).reduce((a, d) => a + d.deep_work, 0)
  const secondHalf = activeDays.slice(half).reduce((a, d) => a + d.deep_work, 0)
  const trend = firstHalf === 0 && secondHalf === 0 ? 'flat'
    : secondHalf > firstHalf * 1.1 ? 'up'
    : secondHalf < firstHalf * 0.9 ? 'down'
    : 'flat'

  // Most distracting app across the week
  const distractionMap: Record<string, string> = {}
  week.forEach(d => { if (d.worst_distraction_app) distractionMap[d.worst_distraction_app] = (distractionMap[d.worst_distraction_app] ?? '') })
  const worstDistraction = week
    .filter(d => d.worst_distraction_app)
    .reduce<Record<string, number>>((acc, d) => {
      acc[d.worst_distraction_app] = (acc[d.worst_distraction_app] ?? 0) + 1
      return acc
    }, {})
  const topDistraction = Object.entries(worstDistraction).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—'
  void distractionMap

  // Average switch rate
  const avgSwitchRate = activeDays.length
    ? (activeDays.reduce((a, d) => a + d.switch_rate, 0) / activeDays.length).toFixed(1)
    : '0'

  // Peak productivity hour (most common peak_hour across active days)
  const hourVotes: Record<number, number> = {}
  activeDays.forEach(d => { if (d.peak_hour >= 0) hourVotes[d.peak_hour] = (hourVotes[d.peak_hour] ?? 0) + 1 })
  const peakHour = Object.entries(hourVotes).sort((a, b) => b[1] - a[1])[0]?.[0]
  const peakHourLabel = peakHour != null ? fmtHour(Number(peakHour)) : '—'

  // Avg focus efficiency
  const avgEfficiency = activeDays.length
    ? Math.round(activeDays.reduce((a, d) => a + d.focus_efficiency, 0) / activeDays.length * 100)
    : 0

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? '#4ecdc4' : trend === 'down' ? '#ff6b6b' : '#6b6b6b'

  // Observer insights text
  const bestDay = activeDays.length > 0
    ? activeDays.reduce((a, b) => a.productivity_score > b.productivity_score ? a : b, activeDays[0])
    : null
  const insights: string[] = []
  if (bestDay) insights.push(`Best day was ${bestDay.day} (${Math.round(bestDay.productivity_score * 100)}% focus score).`)
  if (trend !== 'flat') insights.push(`Deep work is trending ${trend === 'up' ? '↑ up' : '↓ down'} this week.`)
  if (topDistraction !== '—') insights.push(`Most frequent distraction: ${topDistraction}.`)
  if (peakHour) insights.push(`You're most productive around ${peakHourLabel}.`)
  if (avgEfficiency > 0) insights.push(`${avgEfficiency}% of your tracked time is focused work.`)

  return (
    <div>
      <h1 style={{ fontSize: 32, fontWeight: 700, color: '#e5e2e1', letterSpacing: '-0.02em', marginBottom: 24 }}>Weekly Productivity Trends</h1>

      {/* Top KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'AVG. DEEP WORK/DAY', value: fmtDuration(avgDeepWork), accent: '#e5e2e1', sub: `${activeDays.length} active days` },
          { label: 'TOP APP', value: topAppName, sub: fmtDuration(topAppTime), accent: '#4ecdc4' },
          { label: 'TOTAL FOCUS TIME', value: `${(totalFocus / 3600).toFixed(1)}h`, accent: '#f7c948', sub: `${avgSwitchRate} switches/hr avg` },
          { label: 'FOCUS EFFICIENCY', value: `${avgEfficiency}%`, accent: '#568dfe', sub: `peak hour: ${peakHourLabel}` },
        ].map(card => (
          <div key={card.label} style={{ background: '#201f1f', borderRadius: 12, padding: 20, borderTop: `2px solid ${card.accent}33` }}>
            <div style={{ fontSize: 10, color: '#6b6b6b', letterSpacing: '0.1em', marginBottom: 12 }}>{card.label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: card.accent, letterSpacing: '-0.02em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{card.value}</div>
            {card.sub && <div style={{ fontSize: 11, color: '#555', marginTop: 6 }}>{card.sub}</div>}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Deep work bar chart */}
        <div style={{ background: '#201f1f', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#e5e2e1', marginBottom: 4 }}>Weekly Focus Intensity</div>
              <div style={{ fontSize: 12, color: '#555' }}>Deep work vs active time per day</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', background: `${trendColor}15`, borderRadius: 6 }}>
              <TrendIcon size={13} color={trendColor} />
              <span style={{ fontSize: 11, color: trendColor, fontWeight: 600 }}>
                {trend === 'up' ? 'IMPROVING' : trend === 'down' ? 'DECLINING' : 'STEADY'}
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={week} barGap={4} barSize={20}>
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#555', fontSize: 12 }} />
              <YAxis hide />
              <Tooltip content={({ active, payload }) => {
                if (!active || !payload?.[0]) return null
                const d = payload[0].payload as WeekDay
                return (
                  <div style={{ background: 'rgba(32,31,31,0.95)', backdropFilter: 'blur(24px)', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#e5e2e1' }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>{d.date}</div>
                    <div style={{ color: '#6b6b6b' }}>Active: {fmtDuration(d.total_active)}</div>
                    <div style={{ color: '#4f86f7' }}>Deep work: {fmtDuration(d.deep_work)}</div>
                    <div style={{ color: '#4ecdc4' }}>Efficiency: {Math.round(d.focus_efficiency * 100)}%</div>
                    <div style={{ color: '#f7c948' }}>Switch rate: {d.switch_rate}/hr</div>
                    <div style={{ color: '#ff6b6b' }}>Score: {Math.round(d.productivity_score * 100)}%</div>
                  </div>
                )
              }} />
              {/* Total active (background) */}
              <Bar dataKey="total_active" radius={[4, 4, 0, 0]} fill="#2a2a2a" />
              {/* Deep work (foreground) */}
              <Bar dataKey="deep_work" radius={[4, 4, 0, 0]}>
                {week.map((d, i) => (
                  <Cell key={i} fill={d.date === today ? '#568dfe' : d.deep_work > avgDeepWork ? '#4f86f7' : '#3a3a3a'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 11 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#555' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#2a2a2a', border: '1px solid #444', display: 'inline-block' }} /> ACTIVE TIME</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#555' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#4f86f7', display: 'inline-block' }} /> DEEP WORK</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#555' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#568dfe', display: 'inline-block' }} /> TODAY</span>
          </div>
        </div>

        {/* Distraction rate chart */}
        <div style={{ background: '#201f1f', borderRadius: 12, padding: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e5e2e1', marginBottom: 4 }}>Context Switch Rate</div>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 16 }}>Interruptions per hour</div>
          <ResponsiveContainer width="100%" height={130}>
            <LineChart data={week}>
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#555', fontSize: 11 }} />
              <YAxis hide />
              <Tooltip content={({ active, payload }) => {
                if (!active || !payload?.[0]) return null
                const d = payload[0].payload as WeekDay
                return (
                  <div style={{ background: 'rgba(32,31,31,0.95)', borderRadius: 8, padding: '8px 12px', fontSize: 12, color: '#e5e2e1' }}>
                    <div>{d.day}: {d.switch_rate}/hr</div>
                    {d.worst_distraction_app && <div style={{ color: '#555', marginTop: 2 }}>→ {d.worst_distraction_app}</div>}
                  </div>
                )
              }} />
              <Line type="monotone" dataKey="switch_rate" stroke="#f7c948" strokeWidth={2} dot={{ fill: '#f7c948', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ marginTop: 16, padding: '10px 12px', background: '#131313', borderRadius: 8 }}>
            <div style={{ fontSize: 10, color: '#555', letterSpacing: '0.08em', marginBottom: 6 }}>TOP DISTRACTION</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#ff6b6b' }}>{topDistraction}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Activity mix */}
        <div style={{ background: '#201f1f', borderRadius: 12, padding: 24 }}>
          <div style={{ fontSize: 11, color: '#555', letterSpacing: '0.1em', marginBottom: 16 }}>WEEKLY ACTIVITY MIX</div>
          {Object.entries(catTotals).sort((a, b) => b[1] - a[1]).map(([cat, secs]) => {
            const pct = catTotal > 0 ? Math.round((secs / catTotal) * 100) : 0
            const color = CATEGORY_COLORS[cat] ?? '#555'
            return (
              <div key={cat} style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 13 }}>
                  <span style={{ color: '#aaa' }}>{cat}</span>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{ color: '#555', fontSize: 11 }}>{fmtDuration(secs)}</span>
                    <span style={{ color: '#e5e2e1', fontWeight: 600, width: 32, textAlign: 'right' }}>{pct}%</span>
                  </div>
                </div>
                <div style={{ height: 3, background: '#131313', borderRadius: 2 }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 2 }} />
                </div>
              </div>
            )
          })}
          {catTotal === 0 && <div style={{ color: '#555', fontSize: 12 }}>No data this week</div>}
        </div>

        {/* Observer insights */}
        <div style={{ background: '#201f1f', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <TrendingUp size={16} color="#b0c6ff" />
            <span style={{ fontSize: 13, fontWeight: 600, color: '#e5e2e1' }}>Observer Insights</span>
          </div>
          {insights.length > 0
            ? insights.map((insight, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                  <span style={{ color: '#b0c6ff', fontSize: 14, lineHeight: 1.4, flexShrink: 0 }}>·</span>
                  <p style={{ margin: 0, fontSize: 12, color: '#6b6b6b', lineHeight: 1.7 }}>{insight}</p>
                </div>
              ))
            : <p style={{ fontSize: 12, color: '#6b6b6b', lineHeight: 1.7 }}>Start tracking to see personalized insights about your productivity patterns.</p>
          }
        </div>
      </div>
    </div>
  )
}
