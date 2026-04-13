import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { Briefcase, MessageSquare, BookOpen, Gamepad2, HelpCircle } from 'lucide-react'
import { isBrowserApp, parseBrowserTitle } from './utils'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import DailyOverview from './pages/DailyOverview'
import Sessions from './pages/Sessions'
import Trends from './pages/Trends'
import Rules from './pages/Rules'
import './index.css'

export type Page = 'overview' | 'sessions' | 'trends' | 'rules'

export const API = 'http://127.0.0.1:7331'

export type Session = {
  id: number; app_name: string; window_title: string; category: string
  start_time: number; end_time: number; duration: number; is_idle: number
}

export type Summary = {
  total_active: number; deep_work: number; distractions: number
  productivity_score: number; top_apps: { app_name: string; duration: number }[]
  categories: Record<string, number>
}

export const CATEGORY_COLORS: Record<string, string> = {
  Work: '#4f86f7', Communication: '#f7c948', Learning: '#4ecdc4',
  Entertainment: '#ff6b6b', Unknown: '#555'
}

export const CATEGORY_ICONS: Record<string, React.ComponentType<{ size?: number; color?: string }>> = {
  Work: Briefcase,
  Communication: MessageSquare,
  Learning: BookOpen,
  Entertainment: Gamepad2,
  Unknown: HelpCircle,
}

export function AppIcon({ name, windowTitle = '', size = 28 }: { name: string; windowTitle?: string; size?: number }) {
  const colors = ['#4f86f7', '#f7c948', '#4ecdc4', '#ff6b6b', '#b0c6ff', '#568dfe']
  const color = colors[name.charCodeAt(0) % colors.length]

  if (isBrowserApp(name) && windowTitle) {
    const { domain } = parseBrowserTitle(windowTitle)
    if (domain) {
      return (
        <div style={{ width: size, height: size, borderRadius: 6, background: '#1a1a1a', border: '1px solid #2a2a2a', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, overflow: 'hidden' }}>
          <img
            src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
            width={size - 8}
            height={size - 8}
            alt={domain}
            onError={(e) => {
              const el = e.currentTarget
              el.style.display = 'none'
              const parent = el.parentElement
              if (parent) {
                parent.style.background = color + '22'
                parent.style.border = `1px solid ${color}44`
                parent.innerHTML = `<span style="font-size:11px;font-weight:700;color:${color}">${name[0]?.toUpperCase()}</span>`
              }
            }}
          />
        </div>
      )
    }
  }

  return (
    <div style={{ width: size, height: size, borderRadius: 6, background: color + '22', border: `1px solid ${color}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color, flexShrink: 0 }}>
      {name[0]?.toUpperCase()}
    </div>
  )
}

export function CategoryIcon({ category, size = 14 }: { category: string; size?: number }) {
  const Icon = CATEGORY_ICONS[category] ?? HelpCircle
  const color = CATEGORY_COLORS[category] ?? '#555'
  return <Icon size={size} color={color} />
}

export function fmtDuration(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function fmtTime(ts: number): string {
  return new Date(ts * 1000).toTimeString().slice(0, 8)
}

export default function App() {
  const [page, setPage] = useState<Page>('overview')
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'))

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#131313' }}>
      <Sidebar page={page} onNavigate={setPage} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TopBar date={date} onDateChange={setDate} />
        <main style={{ flex: 1, padding: '24px 32px', overflow: 'auto' }}>
          {page === 'overview' && <DailyOverview date={date} />}
          {page === 'sessions' && <Sessions date={date} />}
          {page === 'trends' && <Trends />}
          {page === 'rules' && <Rules />}
        </main>
        <StatusBar />
      </div>
    </div>
  )
}

function StatusBar() {
  const [active, setActive] = useState(false)
  useEffect(() => {
    fetch(`${API}/api/summary?date=${format(new Date(), 'yyyy-MM-dd')}`)
      .then(() => setActive(true)).catch(() => setActive(false))
  }, [])
  return (
    <div style={{ background: '#0e0e0e', borderTop: '1px solid #1a1a1a', padding: '6px 32px', display: 'flex', alignItems: 'center', gap: 24, fontSize: 11, color: '#555', letterSpacing: '0.05em' }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: active ? '#4ecdc4' : '#555', display: 'inline-block' }} />
        {active ? 'OBSERVER ACTIVE' : 'OBSERVER OFFLINE'}
      </span>
      <span>DB: FOCUSLOG.SQLITE</span>
      <span>PRECISION: 5000MS</span>
    </div>
  )
}
