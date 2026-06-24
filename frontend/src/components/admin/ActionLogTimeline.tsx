import { useEffect, useState } from 'react'

interface AgentEvent {
  id: number
  conversationId: string
  timestamp: string
  eventType: string
  payload: Record<string, unknown>
}

function labelForEvent(e: AgentEvent): string {
  switch (e.eventType) {
    case 'tool_call': return `Called browser agent: ${String((e.payload as { input?: string }).input ?? '').slice(0, 80)}`
    case 'tool_result': return `Browser agent returned result`
    case 'browser_action': {
      const p = e.payload as { action?: string; details?: Record<string, unknown> }
      // Generalized reference-based actions
      if (p.action === 'click') return `Clicked element [${p.details?.ref ?? '?'}]`
      if (p.action === 'fill') return `Filled [${p.details?.ref ?? '?'}]: "${String(p.details?.value ?? '').slice(0, 50)}"`
      if (p.action === 'navigate') return `Navigated to: ${String(p.details?.url ?? '')}`
      if (p.action === 'scroll') return `Scrolled ${String(p.details?.direction ?? 'down')}`
      if (p.action === 'go_back') return `Went back to previous page`
      if (p.action === 'read_page') return `Re-read current page`
      // Legacy fallback for historical events
      if (p.action === 'fill_testid') return `Filled field: "${String(p.details?.value ?? '')}"`
      if (p.action === 'click_testid') return `Clicked element: ${String(p.details?.testid ?? '')}`
      if (p.action === 'click_text') return `Clicked: ${String(p.details?.text ?? '')}`
      return `Browser action: ${p.action ?? ''}`
    }
    case 'browser_done': {
      const r = (e.payload as { result?: string }).result ?? ''
      return `Task completed: ${r.slice(0, 80)}`
    }
    case 'agent_escalate': return `Escalated to human agent`
    default: return e.eventType
  }
}

function iconForEvent(eventType: string): string {
  switch (eventType) {
    case 'tool_call': return '🔧'
    case 'tool_result': return '✅'
    case 'browser_action': return '🖱️'
    case 'browser_done': return '✓'
    case 'agent_escalate': return '↗'
    default: return '•'
  }
}

interface Props {
  conversationId: string
}

export default function ActionLogTimeline({ conversationId }: Props) {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [open, setOpen] = useState(true)

  useEffect(() => {
    if (!conversationId) return
    fetch(`/admin/api/conversations/${conversationId}/events`)
      .then((r) => r.json())
      .then(setEvents)
      .catch(() => {})
  }, [conversationId])

  if (events.length === 0) return null

  return (
    <div style={{ marginTop: 24, border: '1px solid #eee', borderRadius: 8 }}>
      <div
        onClick={() => setOpen((o) => !o)}
        style={{ padding: '10px 16px', cursor: 'pointer', fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}
      >
        <span>{open ? '▼' : '▶'}</span>
        Agent Activity ({events.length} event{events.length !== 1 ? 's' : ''})
      </div>
      {open && (
        <div style={{ padding: '8px 16px 16px', display: 'flex', flexDirection: 'column', gap: 0 }}>
          {events.map((e, i) => (
            <div key={e.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', paddingBottom: 8 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                <span style={{ fontSize: 16 }}>{iconForEvent(e.eventType)}</span>
                {i < events.length - 1 && (
                  <div style={{ width: 1, background: '#e0e0e0', flex: 1, minHeight: 16, marginTop: 2 }} />
                )}
              </div>
              <div style={{ paddingTop: 2 }}>
                <div style={{ fontSize: 13 }}>{labelForEvent(e)}</div>
                <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>
                  {new Date(e.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
