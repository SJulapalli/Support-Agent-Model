import { useEffect, useState } from 'react'
import { Order } from '../../types'

const REFUND_CATEGORIES = [
  'Product defect',
  'Wrong item received',
  'Damaged in transit',
  'Changed mind',
  'Other',
]

const PRODUCT_ISSUE_CATEGORIES = new Set(['Product defect', 'Wrong item received', 'Damaged in transit'])

function getRefundTier(category: string, orderAgeDays: number, totalCents: number) {
  const isProductIssue = PRODUCT_ISSUE_CATEGORIES.has(category)

  if (isProductIssue && orderAgeDays <= 30) {
    return { pct: 100, suggestedCents: totalCents, label: 'Full refund — product issue within 30 days', color: '#1a6e3a', bg: '#f0faf4', border: '#6dbb8a' }
  }
  if (isProductIssue && orderAgeDays <= 60) {
    const cents = Math.round(totalCents * 0.75)
    return { pct: 75, suggestedCents: cents, label: '75% partial refund — product issue reported 31–60 days after delivery', color: '#92610a', bg: '#fff8e6', border: '#f5c842' }
  }
  if (isProductIssue) {
    return { pct: 0, suggestedCents: 0, label: 'Escalate — product issue reported more than 60 days after delivery', color: '#cc0000', bg: '#fff0f0', border: '#f5a0a0' }
  }
  if (orderAgeDays <= 30) {
    const cents = Math.round(totalCents * 0.5)
    return { pct: 50, suggestedCents: cents, label: '50% partial refund — customer preference within 30 days', color: '#92610a', bg: '#fff8e6', border: '#f5c842' }
  }
  return { pct: 0, suggestedCents: 0, label: 'No refund — customer preference outside 30-day window', color: '#cc0000', bg: '#fff0f0', border: '#f5a0a0' }
}

interface Props {
  order: Order
  onClose: () => void
  onSuccess: () => void
}

export default function RefundModal({ order, onClose, onSuccess }: Props) {
  const [category, setCategory] = useState('')
  const [details, setDetails] = useState('')
  const [partialAmount, setPartialAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fullAmount = order.totalCents / 100
  const orderAgeDays = Math.floor((Date.now() - new Date(order.createdAt).getTime()) / 86_400_000)
  const tier = category ? getRefundTier(category, orderAgeDays, order.totalCents) : null

  // Auto-populate the partial amount when the tier changes
  useEffect(() => {
    if (!tier) return
    if (tier.pct === 100) {
      setPartialAmount('')
    } else if (tier.pct > 0) {
      setPartialAmount((tier.suggestedCents / 100).toFixed(2))
    } else {
      setPartialAmount('')
    }
  }, [category])

  const parsedPartial = parseFloat(partialAmount)
  const refundAmount = partialAmount && !isNaN(parsedPartial) ? parsedPartial : fullAmount

  const handleSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault()
    if (!category) { setError('Please select a category.'); return }
    if (!details.trim()) { setError('Please provide details.'); return }
    if (tier && tier.pct === 0) { setError('This order is not eligible for a refund under the selected category. Escalate if needed.'); return }
    if (partialAmount && (isNaN(parsedPartial) || parsedPartial <= 0 || parsedPartial > fullAmount)) {
      setError(`Partial amount must be between $0.01 and $${fullAmount.toFixed(2)}.`)
      return
    }
    setError('')
    setLoading(true)
    const body: Record<string, unknown> = { category, reason: details }
    if (partialAmount && !isNaN(parsedPartial)) body.amount_cents = Math.round(parsedPartial * 100)
    await fetch(`/admin/api/orders/${order.id}/refund`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    setLoading(false)
    onSuccess()
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      <div style={{ background: '#fff', borderRadius: 12, padding: 32, width: 480 }}>
        <h3 style={{ marginBottom: 4 }}>Issue Refund — Order #{order.id}</h3>
        <p style={{ color: '#666', fontSize: 13, marginBottom: 20 }}>
          Order total: <strong>${fullAmount.toFixed(2)}</strong> · Age: <strong>{orderAgeDays} day{orderAgeDays !== 1 ? 's' : ''}</strong>
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="refund-category" style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>
            Category
          </label>
          <select
            id="refund-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            required
            style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #ddd', marginBottom: 12, fontSize: 14 }}
          >
            <option value="">Select a category…</option>
            {REFUND_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>

          {tier && (
            <div style={{ background: tier.bg, border: `1px solid ${tier.border}`, borderRadius: 6, padding: '10px 12px', marginBottom: 16, fontSize: 13, color: tier.color, fontWeight: 500 }}>
              {tier.label}
            </div>
          )}

          <label htmlFor="refund-details" style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>
            Details
          </label>
          <textarea
            id="refund-details"
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            placeholder="Describe the issue…"
            required
            rows={3}
            data-testid="refund-reason-input"
            style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #ddd', marginBottom: 16, fontSize: 14, resize: 'vertical', boxSizing: 'border-box' }}
          />

          <label htmlFor="refund-amount" style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>
            {tier && tier.pct < 100 && tier.pct > 0 ? `Partial amount (${tier.pct}% = $${(tier.suggestedCents / 100).toFixed(2)} suggested)` : 'Partial amount (leave blank for full refund)'}
          </label>
          <input
            id="refund-amount"
            type="number"
            value={partialAmount}
            onChange={(e) => setPartialAmount(e.target.value)}
            placeholder={tier && tier.pct === 100 ? 'Full refund' : `e.g. $${tier ? (tier.suggestedCents / 100).toFixed(2) : fullAmount.toFixed(2)}`}
            min="0.01"
            max={fullAmount}
            step="0.01"
            style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #ddd', marginBottom: 8, fontSize: 14, boxSizing: 'border-box' }}
          />
          <p style={{ color: '#888', fontSize: 12, marginBottom: 16 }}>
            Refund amount: <strong>${refundAmount.toFixed(2)}</strong>
          </p>

          {error && <p style={{ color: '#cc0000', fontSize: 13, marginBottom: 12 }}>{error}</p>}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #ddd', cursor: 'pointer', background: '#fff' }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || (tier?.pct === 0)}
              data-testid="confirm-refund-btn"
              style={{ padding: '8px 20px', background: tier?.pct === 0 ? '#aaa' : '#cc0000', color: '#fff', border: 'none', borderRadius: 6, cursor: tier?.pct === 0 ? 'not-allowed' : 'pointer', fontWeight: 600 }}
            >
              {loading ? 'Processing…' : `Confirm Refund ($${refundAmount.toFixed(2)})`}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
