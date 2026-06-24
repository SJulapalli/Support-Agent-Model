import { useState } from 'react'
import { Order } from '../../types'

const CANCEL_REASONS = [
  'Customer request',
  'Out of stock',
  'Payment issue',
  'Other',
]

interface Props {
  order: Order
  onClose: () => void
  onSuccess: () => void
}

export default function CancelModal({ order, onClose, onSuccess }: Props) {
  const [reason, setReason] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault()
    if (!reason) { setError('Please select a reason.'); return }
    setError('')
    setLoading(true)
    await fetch(`/admin/api/orders/${order.id}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: notes ? `[${reason}] ${notes}` : reason }),
    })
    setLoading(false)
    onSuccess()
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      <div style={{ background: '#fff', borderRadius: 12, padding: 32, width: 440 }}>
        <h3 style={{ marginBottom: 4 }}>Cancel Order #{order.id}</h3>
        <p style={{ color: '#cc0000', fontSize: 13, marginBottom: 20 }}>This cannot be undone.</p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="cancel-reason" style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>
            Reason
          </label>
          <select
            id="cancel-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #ddd', marginBottom: 16, fontSize: 14 }}
          >
            <option value="">Select a reason…</option>
            {CANCEL_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>

          <label htmlFor="cancel-notes" style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>
            Notes (optional)
          </label>
          <textarea
            id="cancel-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Additional context…"
            rows={3}
            style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #ddd', marginBottom: 16, fontSize: 14, resize: 'vertical', boxSizing: 'border-box' }}
          />

          {error && <p style={{ color: '#cc0000', fontSize: 13, marginBottom: 12 }}>{error}</p>}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #ddd', cursor: 'pointer', background: '#fff' }}>
              Back
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{ padding: '8px 20px', background: '#cc0000', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}
            >
              {loading ? 'Cancelling…' : 'Confirm Cancellation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}