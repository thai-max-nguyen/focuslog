# Security & Privacy

## What FocusLog records

| Data | Recorded |
|------|----------|
| App name (e.g. "Safari") | ✅ Yes |
| Window title (e.g. "GitHub - focuslog") | ✅ Yes |
| Time spent per app | ✅ Yes |
| Screen content / screenshots | ❌ Never |
| Keystrokes or mouse positions | ❌ Never |
| File contents | ❌ Never |
| Network traffic | ❌ Never |
| Internet requests | ❌ Never |

## Where data lives

```
~/Library/Application Support/focuslog/focuslog.db
```

Standard SQLite file. Never uploaded anywhere. You own it.

## Why Screen Recording permission is required

macOS requires the Screen Recording entitlement to read window title text via
`CGWindowListCopyWindowInfo`. FocusLog uses this **only** to log the active window title.
No screen images are ever captured or stored.

To revoke at any time: System Settings → Privacy & Security → Screen Recording → disable FocusLog.

## Reporting vulnerabilities

Open a GitHub issue with the label `security`.
