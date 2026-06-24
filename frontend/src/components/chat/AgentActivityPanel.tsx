import { useState } from 'react'
import { ActionLogEvent } from '../../hooks/useChat'

function labelForEvent(e: ActionLogEvent): string {
  switch (e.event_type) {
    case 'tool_call': return `Called browser agent: ${String((e.payload as { input?: string }).input ?? '').slice(0, 60)}`
    case 'tool_result': return `Agent returned result`
    case 'browser_action': {
      const p = e.payload as { action?: string; details?: Record<string, unknown> }
      // Generalized reference-based actions
      if (p.action === 'click') return `Clicked element [${p.details?.ref ?? '?'}]`
      if (p.action === 'fill') return `Filled [${p.details?.ref ?? '?'}]: "${String(p.details?.value ?? '').slice(0, 40)}"`
      if (p.action === 'navigate') return `Navigated to: ${String(p.details?.url ?? '')}`
      if (p.action === 'scroll') return `Scrolled ${String(p.details?.direction ?? 'down')}`
      if (p.action === 'go_back') return `Went back`
      if (p.action === 'read_page') return `Re-read page`
      // Legacy fallback for historical events
      if (p.action === 'fill_testid') return `Filled: "${String(p.details?.value ?? '')}"`
      if (p.action === 'click_testid') return `Clicked: ${String(p.details?.testid ?? '')}`
      if (p.action === 'click_text') return `Clicked: ${String(p.details?.text ?? '')}`
      return `Browser action: ${p.action ?? ''}`
    }
    case 'browser_done': return `Browser completed task`
    case 'agent_escalate': return `Escalated to human agent`
    default: return e.event_type
  }
}

interface Props {
  events: ActionLogEvent[]
}

export default function AgentActivityPanel({ events }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div style={{ background: '#f8f9fa', border: '1px solid #e9ecef', borderRadius: 8, padding: '10px 12px', fontSize: 12, color: '#555' }}>
      <div
        onClick={(e) => { e.stopPropagation(); setCollapsed((c) => !c) }}
        style={{ cursor: 'pointer', fontWeight: 600, marginBottom: collapsed ? 0 : 6, display: 'flex', alignItems: 'center', gap: 6 }}
      >
        <span>{collapsed ? '▶' : '▼'}</span>
        Agent working... ({events.length} step{events.length !== 1 ? 's' : ''})
      </div>
      {!collapsed && events.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 4 }}>
          {events.map((e, i) => (
            <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
              <span style={{ color: '#aaa', flexShrink: 0 }}>•</span>
              <span>{labelForEvent(e)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
