import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { API, CATEGORY_COLORS } from '../App'

type Rule = { id: number; app_name: string | null; url_contains: string | null; category: string }

export default function Rules() {
  const [rules, setRules] = useState<Rule[]>([])
  const [appName, setAppName] = useState('')
  const [urlContains, setUrlContains] = useState('')
  const [category, setCategory] = useState('Work')

  const load = () => fetch(`${API}/api/rules`).then(r => r.json()).then(setRules).catch(() => {})
  useEffect(() => { load() }, [])

  const addRule = async () => {
    if (!appName && !urlContains) return
    await fetch(`${API}/api/rules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ app_name: appName || null, url_contains: urlContains || null, category }) })
    setAppName(''); setUrlContains(''); load()
  }

  const deleteRule = async (id: number) => {
    await fetch(`${API}/api/rules/${id}`, { method: 'DELETE' })
    load()
  }

  return (
    <div>
      <h1 style={{ fontSize: 32, fontWeight: 700, color: '#e5e2e1', letterSpacing: '-0.02em', marginBottom: 8 }}>Classification Rules</h1>
      <p style={{ fontSize: 13, color: '#6b6b6b', marginBottom: 32, lineHeight: 1.6 }}>
        Define how FocusLog interprets your activity. Rules are processed from top to bottom.<br />Once a match is found, subsequent rules are ignored.
      </p>

      <div style={{ background: '#201f1f', borderRadius: 12, overflow: 'hidden', marginBottom: 40 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 160px 60px', gap: 16, padding: '12px 24px', fontSize: 11, color: '#555', letterSpacing: '0.08em', borderBottom: '1px solid #131313' }}>
          <span>APP NAME</span><span>URL CONTAINS</span><span>CATEGORY</span><span>ACTION</span>
        </div>
        {rules.map(rule => {
          const color = CATEGORY_COLORS[rule.category] ?? '#555'
          return (
            <div key={rule.id} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 160px 60px', gap: 16, padding: '16px 24px', alignItems: 'center', borderBottom: '1px solid #131313' }}>
              <span style={{ fontSize: 13, color: '#e5e2e1' }}>{rule.app_name || '—'}</span>
              <span style={{ fontSize: 12, color: '#6b6b6b' }}>{rule.url_contains || '—'}</span>
              <span style={{ display: 'inline-block', padding: '3px 12px', borderRadius: 20, background: color + '22', color, fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', width: 'fit-content' }}>
                {rule.category.toUpperCase()}
              </span>
              <button onClick={() => deleteRule(rule.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#555', display: 'flex', padding: 4, borderRadius: 4 }}>
                <Trash2 size={14} />
              </button>
            </div>
          )
        })}
        {rules.length === 0 && <div style={{ padding: '32px 24px', color: '#555', fontSize: 13 }}>No custom rules yet.</div>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 40, alignItems: 'start' }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 600, color: '#e5e2e1', marginBottom: 8 }}>Add New Rule</h2>
          <p style={{ fontSize: 13, color: '#6b6b6b', lineHeight: 1.6 }}>Custom rules override default behavior for specific workflows.</p>
        </div>
        <div style={{ background: '#201f1f', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            {[{ label: 'APP NAME', val: appName, set: setAppName, ph: 'e.g. Figma' }, { label: 'URL PATTERN', val: urlContains, set: setUrlContains, ph: 'e.g. figma.com/file' }].map(f => (
              <div key={f.label}>
                <label style={{ fontSize: 10, color: '#6b6b6b', letterSpacing: '0.1em', display: 'block', marginBottom: 8 }}>{f.label}</label>
                <input value={f.val} onChange={e => f.set(e.target.value)} placeholder={f.ph}
                  style={{ width: '100%', background: '#0e0e0e', border: 'none', borderRadius: 8, padding: '12px 14px', color: '#e5e2e1', fontSize: 13, outline: 'none' }} />
              </div>
            ))}
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 10, color: '#6b6b6b', letterSpacing: '0.1em', display: 'block', marginBottom: 8 }}>CATEGORY</label>
            <select value={category} onChange={e => setCategory(e.target.value)}
              style={{ width: '100%', background: '#0e0e0e', border: 'none', borderRadius: 8, padding: '12px 14px', color: '#e5e2e1', fontSize: 13, cursor: 'pointer', outline: 'none' }}>
              {['Work','Communication','Learning','Entertainment','Unknown'].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <button onClick={addRule} style={{ width: '100%', background: 'linear-gradient(135deg, #b0c6ff, #568dfe)', border: 'none', borderRadius: 8, padding: '13px', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.15)' }}>
            + Add Rule
          </button>
        </div>
      </div>
    </div>
  )
}
