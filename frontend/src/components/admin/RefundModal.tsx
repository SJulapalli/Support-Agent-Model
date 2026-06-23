import { useState } from 'react'
import { Order } from '../../types'

interface Props {
  order: Order
  onClose: () => void
  onSuccess: () => void
}

export default function RefundModal({ order, onClose, onSuccess }: Props) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    await fetch(`/admin/api/orders/${order.id}/refund`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    })
    setLoading(false)
    onSuccess()
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#fff', borderRadius: 12, padding: 32, width: 400 }}>
        <h3>Issue Refund — Order #{order.id}</h3>
        <p>Amount: ${(order.totalCents / 100).toFixed(2)}</p>
        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', marginBottom: 8 }}>Reason</label>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Customer requested refund"
            required
            data-testid="refund-reason-input"
            style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #ddd', marginBottom: 16 }}
          />
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} style={{ padding: '8px 16px' }}>Cancel</button>
            <button
              type="submit"
              disabled={loading}
              data-testid="confirm-refund-btn"
              style={{ padding: '8px 16px', background: '#cc0000', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
            >
              {loading ? 'Processing...' : 'Confirm Refund'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
