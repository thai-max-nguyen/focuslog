import { useState } from 'react'
import { format } from 'date-fns'
import Timeline from './components/Timeline'
import CategoryPie from './components/CategoryPie'
import Leaderboard from './components/Leaderboard'
import Header from './components/Header'
import './App.css'

export type Session = {
  id: number
  app_name: string
  window_title: string
  category: string
  start_time: number
  end_time: number
  duration: number
}

export type Summary = {
  total_active: number
  deep_work: number
  distractions: number
  productivity_score: number
  top_apps: { app_name: string; duration: number }[]
  categories: Record<string, number>
}

const API = 'http://127.0.0.1:7331'

export async function fetchSummary(date: string): Promise<Summary> {
  const res = await fetch(`${API}/api/summary?date=${date}`)
  if (!res.ok) throw new Error('Failed to fetch summary')
  return res.json()
}

export async function fetchTimeline(date: string): Promise<Session[]> {
  const res = await fetch(`${API}/api/timeline?date=${date}`)
  if (!res.ok) throw new Error('Failed to fetch timeline')
  return res.json()
}

export default function App() {
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'))

  return (
    <div className="app">
      <Header date={date} onDateChange={setDate} />
      <main>
        <Timeline date={date} />
        <div className="bottom-row">
          <CategoryPie date={date} />
          <Leaderboard date={date} />
        </div>
      </main>
    </div>
  )
}
