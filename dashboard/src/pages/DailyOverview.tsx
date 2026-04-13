import { useEffect, useRef, useState } from 'react'
import { API, type Summary, type Session, type CurrentSession, CATEGORY_COLORS, AppIcon, CategoryIcon, fmtDuration, fmtTime } from '../App'

function useSummary(date: string, refreshKey: number) {
  const [data, setData] = useState<Summary | null>(null)
  useEffect(() => {
    fetch(`${API}/api/summary?date=${date}`).then(r => r.json()).then(setData).catch(() => {})
  }, [date, refreshKey])
  return data
}

function useTimeline(date: string, refreshKey: number) {
  const [blocks, setBlocks] = useState<Session[]>([])
  useEffect(() => {
    fetch(`${API}/api/timeline?date=${date}`).then(r => r.json()).then(setBlocks).catch(() => {})
  }, [date, refreshKey])
  return blocks
}

function useCurrentSession(refreshKey: number): CurrentSession | null {
  const [session, setSession] = useState<CurrentSession | null>(null)
  useEffect(() => {
    fetch(`${API}/api/current`).then(r => r.json()).then(d => setSession(d || null)).catch(() => setSession(null))
  }, [refreshKey])
  return session
}

/** Live-ticking duration starting from a Unix timestamp. Updates every second. */
function useLiveDuration(startTime: number | null): number {
  const [elapsed, setElapsed] = useState(0)
  const rafRef = useRef<ReturnType<typeof setInterval> | null>(null)
  useEffect(() => {
    if (!startTime) { setElapsed(0); return }
    const tick = () => setElapsed(Math.floor(Date.now() / 1000) - startTime)
    tick()
    rafRef.current = setInterval(tick, 1000)
    return () => { if (rafRef.current) clearInterval(rafRef.current) }
  }, [startTime])
  return elapsed
}

function FocusRing({ score }: { score: number }) {
  const r = 90, cx = 110, cy = 110
  const circumference = 2 * Math.PI * r
  const progress = circumference * (1 - score)
  return (
    <svg width={220} height={220} style={{ display: 'block', margin: '0 auto' }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#2a2a2a" strokeWidth={8} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#568dfe" strokeWidth={8}
        strokeDasharray={circumference} strokeDashoffset={progress}
        strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 1s ease' }} />
      <text x={cx} y={cy - 8} textAnchor="middle" fill="#e5e2e1" fontSize={36} fontWeight={700} fontFamily="Inter" letterSpacing="-1">{Math.round(score * 100)}%</text>
      <text x={cx} y={cy + 16} textAnchor="middle" fill="#6b6b6b" fontSize={10} fontFamily="Inter" letterSpacing="2">PRODUCTIVITY SCORE</text>
    </svg>
  )
}

function fmtHour(h: number): string {
  if (h < 0) return '—'
  if (h === 0) return '12am'
  if (h < 12) return `${h}am`
  if (h === 12) return '12pm'
  return `${h - 12}pm`
}

export default function DailyOverview({ date, refreshKey }: { date: string; refreshKey: number }) {
  const summary = useSummary(date, refreshKey)
  const blocks = useTimeline(date, refreshKey)
  const isToday = date === new Date().toISOString().slice(0, 10)
  const current = isToday ? useCurrentSession(refreshKey) : null  // eslint-disable-line react-hooks/rules-of-hooks
  const liveElapsed = useLiveDuration(current?.start_time ?? null)
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null)
  const DAY = 86400

  // Anchor timeline to local midnight of the selected date
  const dayStart = (() => {
    const [y, m, d] = date.split('-').map(Number)
    return Math.floor(new Date(y, m - 1, d).getTime() / 1000)
  })()

  const totalCat = summary
    ? Object.entries(summary.categories)
        .filter(([k]) => k !== 'Unknown' && k !== 'Idle')
        .reduce((a, [, b]) => a + b, 0)
    : 0

  const visibleBlocks = blocks.filter(b => b.category !== 'Idle')
  const idleBlocks = blocks.filter(b => b.category === 'Idle')

  return (
    <div>
      {/* Now Playing banner — live in-memory session */}
      {current && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 14,
          background: '#1a1f2e', border: '1px solid #2a3a5e',
          borderRadius: 10, padding: '12px 18px', marginBottom: 20,
        }}>
          {/* Pulsing dot */}
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: CATEGORY_COLORS[current.category] ?? '#568dfe',
            flexShrink: 0,
            boxShadow: `0 0 0 3px ${(CATEGORY_COLORS[current.category] ?? '#568dfe')}33`,
            animation: 'pulse 1.5s infinite',
          }} />
          <AppIcon name={current.app_name} size={26} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e5e2e1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {current.app_name}
            </div>
            {current.window_title && (
              <div style={{ fontSize: 11, color: '#555', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {current.window_title}
              </div>
            )}
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: CATEGORY_COLORS[current.category] ?? '#568dfe', letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
              {fmtDuration(liveElapsed)}
            </div>
            <div style={{ fontSize: 10, color: '#555', letterSpacing: '0.08em', marginTop: 2 }}>
              AND COUNTING
            </div>
          </div>
          <div style={{ padding: '3px 8px', background: `${CATEGORY_COLORS[current.category] ?? '#568dfe'}22`, borderRadius: 4, fontSize: 10, color: CATEGORY_COLORS[current.category] ?? '#568dfe', letterSpacing: '0.06em', flexShrink: 0 }}>
            {current.category.toUpperCase()}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: '#e5e2e1' }}>Activity Timeline</span>
          <div style={{ display: 'flex', gap: 16 }}>
            {Object.entries(CATEGORY_COLORS).filter(([k]) => k !== 'Unknown' && k !== 'Idle').map(([cat, color]) => (
              <span key={cat} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: '#6b6b6b', letterSpacing: '0.06em' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, display: 'inline-block' }} />
                {cat.toUpperCase().slice(0, 5)}
              </span>
            ))}
          </div>
        </div>
        <div style={{ position: 'relative', height: 40, background: '#0e0e0e', borderRadius: 8, overflow: 'hidden' }}>
          {/* Idle gaps as slightly lighter dark segments */}
          {idleBlocks.map((b, i) => {
            const left = ((b.start_time - dayStart) / DAY) * 100
            const width = Math.max((b.duration / DAY) * 100, 0.05)
            return (
              <div key={`idle-${i}`}
                style={{ position: 'absolute', left: `${left}%`, width: `${width}%`, top: 0, height: '100%', background: '#1a1a1a' }} />
            )
          })}
          {/* Active sessions */}
          {visibleBlocks.map((b, i) => {
            const left = ((b.start_time - dayStart) / DAY) * 100
            const width = Math.max((b.duration / DAY) * 100, 0.1)
            return (
              <div key={i}
                onMouseEnter={e => setTooltip({ text: `${b.app_name} · ${b.category} · ${fmtDuration(b.duration)}`, x: e.clientX, y: e.clientY })}
                onMouseLeave={() => setTooltip(null)}
                style={{ position: 'absolute', left: `${left}%`, width: `${width}%`, top: 0, height: '100%', background: CATEGORY_COLORS[b.category] ?? '#555', opacity: 0.9 }} />
            )
          })}
          {blocks.length === 0 && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#555', fontSize: 12 }}>No activity recorded</div>}
          {/* Peak hour marker */}
          {summary && summary.peak_hour >= 0 && (
            <div style={{
              position: 'absolute',
              left: `${(summary.peak_hour / 24) * 100}%`,
              top: 0, height: '100%', width: 2,
              background: 'rgba(255,255,255,0.15)',
              pointerEvents: 'none',
            }} />
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 10, color: '#555' }}>
          {['12am','3am','6am','9am','12pm','3pm','6pm','9pm','12am'].map(t => <span key={t}>{t}</span>)}
        </div>
        {summary && summary.peak_hour >= 0 && (
          <div style={{ fontSize: 10, color: '#555', marginTop: 4, textAlign: 'right' }}>
            Peak focus: <span style={{ color: '#b0c6ff' }}>{fmtHour(summary.peak_hour)}</span>
          </div>
        )}
      </div>

      {tooltip && (
        <div style={{ position: 'fixed', left: tooltip.x + 12, top: tooltip.y - 36, background: 'rgba(32,31,31,0.9)', backdropFilter: 'blur(24px)', borderRadius: 8, padding: '7px 12px', fontSize: 12, color: '#e5e2e1', pointerEvents: 'none', zIndex: 999, boxShadow: '0 8px 40px rgba(176,198,255,0.08)' }}>
          {tooltip.text}
        </div>
      )}

      {/* Bottom row */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 20 }}>
        {/* Left: Focus Ring + Stats */}
        <div style={{ background: '#201f1f', borderRadius: 12, padding: '24px 20px' }}>
          <FocusRing score={summary?.productivity_score ?? 0} />

          {/* Primary stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 20, padding: '16px', background: '#131313', borderRadius: 10 }}>
            {[
              { label: 'ACTIVE TIME', value: fmtDuration(summary?.total_active ?? 0), color: '#e5e2e1' },
              { label: 'DEEP WORK', value: fmtDuration(summary?.deep_work ?? 0), color: '#4f86f7' },
              { label: 'DISTRACTIONS', value: String(summary?.distractions ?? 0), color: '#ff6b6b' },
            ].map(s => (
              <div key={s.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: '#555', letterSpacing: '0.08em', marginBottom: 6 }}>{s.label}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: s.color, letterSpacing: '-0.02em' }}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Secondary stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
            {[
              {
                label: 'LONGEST SESSION',
                value: summary?.longest_session ? fmtDuration(summary.longest_session) : '—',
                sub: summary?.longest_session_app || '',
                color: '#4ecdc4',
              },
              {
                label: 'SWITCH RATE',
                value: summary?.switch_rate != null ? `${summary.switch_rate}/hr` : '—',
                sub: summary?.worst_distraction_app ? `→ ${summary.worst_distraction_app}` : '',
                color: '#f7c948',
              },
              {
                label: 'FOCUS EFFICIENCY',
                value: summary?.focus_efficiency != null ? `${Math.round(summary.focus_efficiency * 100)}%` : '—',
                sub: 'work / active time',
                color: '#568dfe',
              },
              {
                label: 'PEAK HOUR',
                value: summary?.peak_hour != null ? fmtHour(summary.peak_hour) : '—',
                sub: 'most active hour',
                color: '#b0c6ff',
              },
            ].map(s => (
              <div key={s.label} style={{ background: '#131313', borderRadius: 8, padding: '10px 12px' }}>
                <div style={{ fontSize: 9, color: '#555', letterSpacing: '0.08em', marginBottom: 5 }}>{s.label}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: s.color, letterSpacing: '-0.02em' }}>{s.value}</div>
                {s.sub && <div style={{ fontSize: 10, color: '#555', marginTop: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.sub}</div>}
              </div>
            ))}
          </div>

          {/* Allocation breakdown */}
          {summary && totalCat > 0 && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 10, color: '#555', letterSpacing: '0.1em', marginBottom: 12 }}>ALLOCATION BREAKDOWN</div>
              {Object.entries(summary.categories)
                .filter(([cat]) => cat !== 'Unknown' && cat !== 'Idle')
                .sort(([, a], [, b]) => b - a)
                .map(([cat, secs]) => (
                  <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <div style={{ width: 3, height: 24, borderRadius: 2, background: CATEGORY_COLORS[cat] ?? '#555', flexShrink: 0 }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <CategoryIcon category={cat} size={12} />
                      <span style={{ flex: 1, fontSize: 12, color: '#aaa' }}>{cat}</span>
                    </div>
                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, color: '#555' }}>{fmtDuration(secs)}</span>
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#e5e2e1', width: 32, textAlign: 'right' }}>{Math.round((secs / totalCat) * 100)}%</span>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Right: App Hierarchy */}
        <div style={{ background: '#201f1f', borderRadius: 12, padding: '24px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#e5e2e1' }}>App Hierarchy</span>
            <span style={{ fontSize: 10, color: '#555', letterSpacing: '0.08em' }}>USAGE INTENSITY</span>
          </div>
          {(summary?.top_apps ?? []).slice(0, 8).map((app, i) => {
            const maxDur = summary!.top_apps[0]?.duration ?? 1
            const pct = (app.duration / maxDur) * 100
            const cat = Object.entries(summary?.categories ?? {}).length > 0
              ? undefined  // category not in top_apps, color by rank
              : undefined
            void cat
            return (
              <div key={app.app_name} style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
                <span style={{ fontSize: 11, color: '#555', width: 20, flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <AppIcon name={app.app_name} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{ fontSize: 13, color: '#e5e2e1', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{app.app_name}</span>
                    <span style={{ fontSize: 12, color: '#6b6b6b', flexShrink: 0, marginLeft: 8 }}>{fmtDuration(app.duration)}</span>
                  </div>
                  <div style={{ height: 3, background: '#131313', borderRadius: 2 }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: '#568dfe', borderRadius: 2, transition: 'width 0.6s ease' }} />
                  </div>
                </div>
              </div>
            )
          })}
          {(summary?.top_apps ?? []).length === 0 && (
            <div style={{ color: '#555', textAlign: 'center', padding: '40px 0', fontSize: 13 }}>No activity recorded for this day</div>
          )}
        </div>
      </div>
    </div>
  )
}

// Suppress unused import warning — fmtTime is exported for use in other files
void fmtTime
