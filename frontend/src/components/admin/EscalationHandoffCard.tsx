interface HandoffData {
  conversationId: string
  reason?: string
  customer?: string
  ordersReviewed?: string[]
  actionsAttempted?: string[]
  sentiment?: string
  recommendedNextStep?: string
  createdAt: string
}

const sentimentStyle: Record<string, { background: string; color: string }> = {
  frustrated: { background: '#fde8e8', color: '#c0392b' },
  neutral: { background: '#eef2ff', color: '#3730a3' },
  satisfied: { background: '#d1fae5', color: '#065f46' },
}

interface Props {
  handoff: HandoffData
}

export default function EscalationHandoffCard({ handoff }: Props) {
  const sentiment = handoff.sentiment?.toLowerCase() ?? 'neutral'
  const badge = sentimentStyle[sentiment] ?? sentimentStyle.neutral

  return (
    <div style={{ background: '#fffbeb', border: '1px solid #fbbf24', borderRadius: 8, padding: 16, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>⚠ Escalation Handoff</span>
        <span style={{ ...badge, borderRadius: 12, padding: '2px 10px', fontSize: 12, fontWeight: 600 }}>
          {sentiment}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 24px', fontSize: 13 }}>
        <div>
          <div style={{ color: '#888', fontSize: 11, marginBottom: 2 }}>REASON</div>
          <div>{handoff.reason ?? '—'}</div>
        </div>
        <div>
          <div style={{ color: '#888', fontSize: 11, marginBottom: 2 }}>CUSTOMER</div>
          <div>{handoff.customer ?? '—'}</div>
        </div>
        <div>
          <div style={{ color: '#888', fontSize: 11, marginBottom: 2 }}>ORDERS REVIEWED</div>
          <div>{handoff.ordersReviewed?.join(', ') || '—'}</div>
        </div>
        <div>
          <div style={{ color: '#888', fontSize: 11, marginBottom: 2 }}>ACTIONS ATTEMPTED</div>
          <div>{handoff.actionsAttempted?.join('; ') || '—'}</div>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <div style={{ color: '#888', fontSize: 11, marginBottom: 2 }}>RECOMMENDED NEXT STEP</div>
          <div style={{ fontWeight: 600 }}>{handoff.recommendedNextStep ?? '—'}</div>
        </div>
      </div>
      <div style={{ marginTop: 10, fontSize: 11, color: '#aaa' }}>
        Escalated at {new Date(handoff.createdAt).toLocaleString()}
      </div>
    </div>
  )
}
