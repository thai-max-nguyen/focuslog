const BROWSER_APPS = ['arc', 'chrome', 'safari', 'firefox', 'edge', 'brave', 'opera', 'vivaldi']

const BROWSER_SUFFIXES = [
  / · Arc$/i,
  / - Google Chrome$/i,
  / - Chrome$/i,
  / \| Firefox$/i,
  / - Firefox$/i,
  / - Safari$/i,
  / - Microsoft Edge$/i,
  / - Brave$/i,
  / - Opera$/i,
]

export function isBrowserApp(appName: string): boolean {
  const lower = appName.toLowerCase()
  return BROWSER_APPS.some(b => lower.includes(b))
}

export function parseBrowserTitle(windowTitle: string): { cleanTitle: string; domain: string } {
  let clean = windowTitle
  for (const suffix of BROWSER_SUFFIXES) {
    clean = clean.replace(suffix, '')
  }
  clean = clean.trim()

  const domainMap: Record<string, string> = {
    'github': 'github.com',
    'youtube': 'youtube.com',
    'gmail': 'gmail.com',
    'google': 'google.com',
    'stackoverflow': 'stackoverflow.com',
    'reddit': 'reddit.com',
    'twitter': 'twitter.com',
    'x.com': 'x.com',
    'notion': 'notion.so',
    'figma': 'figma.com',
    'linear': 'linear.app',
    'slack': 'slack.com',
    'jira': 'atlassian.net',
    'confluence': 'atlassian.net',
    'claude': 'claude.ai',
    'chatgpt': 'openai.com',
    'netflix': 'netflix.com',
    'spotify': 'spotify.com',
    'vercel': 'vercel.com',
    'railway': 'railway.app',
  }

  const titleLower = clean.toLowerCase()
  for (const [key, domain] of Object.entries(domainMap)) {
    if (titleLower.includes(key)) return { cleanTitle: clean, domain }
  }

  const firstWord = clean.split(/[\s\-–|·]/)[0].trim().toLowerCase()
  if (firstWord.length > 2) return { cleanTitle: clean, domain: `${firstWord}.com` }

  return { cleanTitle: clean, domain: '' }
}
