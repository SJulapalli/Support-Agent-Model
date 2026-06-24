import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface ConversationSummary {
  conversationId: string
  firstEvent: string
  lastEvent: string
  eventCount: number
  escalated: boolean
  customer: string | null
  escalationReason: string | null
  orderIds: number[]
}

export default function ConversationList() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/admin/api/conversations').then((r) => r.json()).then(setConversations).catch(() => {})
  }, [])

  function handleRowClick(c: ConversationSummary) {
    const orderId = c.orderIds[0]
    if (orderId) {
      navigate(`/admin/orders/${orderId}?conversation=${c.conversationId}`)
    } else {
      navigate(`/admin/conversations/${c.conversationId}`)
    }
  }

  if (conversations.length === 0) {
    return (
      <p style={{ color: '#888', marginTop: 32 }}>
        No conversations yet. Start a chat to see agent activity here.
      </p>
    )
  }

  return (
    <div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #eee', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>Conversation</th>
            <th style={{ padding: 8 }}>Status</th>
            <th style={{ padding: 8 }}>Customer</th>
            <th style={{ padding: 8 }}>Orders Viewed</th>
            <th style={{ padding: 8 }}>Events</th>
            <th style={{ padding: 8 }}>Started</th>
            <th style={{ padding: 8 }}>Last Activity</th>
          </tr>
        </thead>
        <tbody>
          {conversations.map((c) => (
            <tr
              key={c.conversationId}
              onClick={() => handleRowClick(c)}
              style={{ borderBottom: '1px solid #eee', cursor: 'pointer' }}
            >
              <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 12, color: '#666' }}>
                {c.conversationId.slice(0, 8)}…
              </td>
              <td style={{ padding: 8 }}>
                {c.escalated ? (
                  <span style={{ background: '#fff0f0', color: '#cc0000', padding: '2px 8px', borderRadius: 12, fontSize: 12, fontWeight: 600 }}>
                    Escalated
                  </span>
                ) : (
                  <span style={{ background: '#f0fff4', color: '#006600', padding: '2px 8px', borderRadius: 12, fontSize: 12 }}>
                    Resolved
                  </span>
                )}
              </td>
              <td style={{ padding: 8 }}>{c.customer ?? '—'}</td>
              <td style={{ padding: 8 }}>
                {c.orderIds.length > 0 ? c.orderIds.map((id) => `#${id}`).join(', ') : '—'}
              </td>
              <td style={{ padding: 8 }}>{c.eventCount}</td>
              <td style={{ padding: 8 }}>{new Date(c.firstEvent).toLocaleString()}</td>
              <td style={{ padding: 8 }}>{new Date(c.lastEvent).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}