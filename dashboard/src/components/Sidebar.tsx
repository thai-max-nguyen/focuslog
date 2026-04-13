import { LayoutDashboard, Clock, TrendingUp, Settings } from 'lucide-react'
import type { Page } from '../App'

const NAV = [
  { id: 'overview' as Page, label: 'DAILY OVERVIEW', icon: LayoutDashboard },
  { id: 'sessions' as Page, label: 'SESSIONS', icon: Clock },
  { id: 'trends' as Page, label: 'TRENDS', icon: TrendingUp },
  { id: 'rules' as Page, label: 'RULES/SETTINGS', icon: Settings },
]

export default function Sidebar({ page, onNavigate }: { page: Page; onNavigate: (p: Page) => void }) {
  return (
    <div style={{ width: 240, minHeight: '100vh', background: '#0e0e0e', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
      <div style={{ padding: '28px 24px 32px' }}>
        <div style={{ fontSize: 20, fontWeight: 700, color: '#e5e2e1', letterSpacing: '-0.02em' }}>FocusLog</div>
        <div style={{ fontSize: 10, color: '#555', letterSpacing: '0.12em', marginTop: 4 }}>THE MONOLITH OBSERVER</div>
      </div>
      <nav style={{ flex: 1, padding: '0 12px' }}>
        {NAV.map(({ id, label, icon: Icon }) => {
          const active = page === id
          return (
            <button key={id} onClick={() => onNavigate(id)} style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 12px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: active ? '#201f1f' : 'transparent',
              color: active ? '#e5e2e1' : '#555',
              fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
              marginBottom: 2, textAlign: 'left',
              borderLeft: active ? '2px solid #568dfe' : '2px solid transparent',
              transition: 'all 0.15s',
            }}>
              <Icon size={15} strokeWidth={active ? 2 : 1.5} />
              {label}
            </button>
          )
        })}
      </nav>
      <div style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#2a2a2a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, color: '#b0c6ff' }}>
          U
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 500, color: '#e5e2e1' }}>You</div>
          <div style={{ fontSize: 10, color: '#555' }}>Local Observer</div>
        </div>
      </div>
    </div>
  )
}
