import { useParams, useNavigate } from 'react-router-dom'
import ActionLogTimeline from './ActionLogTimeline'
import EscalationHandoffCard from './EscalationHandoffCard'
import { useEffect, useState } from 'react'

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

export default function ConversationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [handoff, setHandoff] = useState<HandoffData | null>(null)

  useEffect(() => {
    if (!id) return
    fetch(`/admin/api/conversations/${id}/handoff`)
      .then((r) => r.json())
      .then((d) => { if (d) setHandoff(d) })
      .catch(() => {})
  }, [id])

  if (!id) return null

  return (
    <div>
      <button onClick={() => navigate('/admin/conversations')} style={{ marginBottom: 16 }}>
        ← Back to Conversations
      </button>
      <h2>Conversation</h2>
      <p style={{ fontFamily: 'monospace', color: '#666', marginBottom: 24 }}>{id}</p>

      {handoff && <EscalationHandoffCard handoff={handoff} />}
      <ActionLogTimeline conversationId={id} />
    </div>
  )
}