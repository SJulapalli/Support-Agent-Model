import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { Order, Refund } from '../../types'
import RefundModal from './RefundModal'
import CancelModal from './CancelModal'
import ActionLogTimeline from './ActionLogTimeline'
import EscalationHandoffCard from './EscalationHandoffCard'

function parseRefundReason(reason: string): { category: string | null; details: string } {
  const m = reason.match(/^\[(.+?)\]\s*(.*)$/)
  return m ? { category: m[1], details: m[2].trim() } : { category: null, details: reason }
}

function RefundDetailsCard({ refund, orderTotal }: { refund: Refund; orderTotal: number }) {
  const { category, details } = parseRefundReason(refund.reason)
  const isPartial = refund.amountCents < orderTotal
  const pct = Math.round((refund.amountCents / orderTotal) * 100)

  return (
    <div style={{ background: '#f0faf4', border: '1px solid #6dbb8a', borderRadius: 8, padding: 16, marginTop: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: '#1a6e3a' }}>
          {isPartial ? `Partial Refund Issued (${pct}%)` : 'Full Refund Issued'}
        </span>
        <span style={{ fontWeight: 700, fontSize: 16, color: '#1a6e3a' }}>
          ${(refund.amountCents / 100).toFixed(2)}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px', fontSize: 13 }}>
        {category && (
          <div>
            <div style={{ color: '#666', fontSize: 11, marginBottom: 2 }}>CATEGORY</div>
            <span style={{ background: '#d4edda', color: '#1a6e3a', padding: '2px 8px', borderRadius: 10, fontSize: 12, fontWeight: 600 }}>
              {category}
            </span>
          </div>
        )}
        <div>
          <div style={{ color: '#666', fontSize: 11, marginBottom: 2 }}>STATUS</div>
          <div>{refund.status}</div>
        </div>
        {details && (
          <div style={{ gridColumn: '1 / -1' }}>
            <div style={{ color: '#666', fontSize: 11, marginBottom: 2 }}>DETAILS</div>
            <div>{details}</div>
          </div>
        )}
        <div style={{ gridColumn: '1 / -1' }}>
          <div style={{ color: '#666', fontSize: 11, marginBottom: 2 }}>ISSUED</div>
          <div>{new Date(refund.createdAt).toLocaleString()}</div>
        </div>
      </div>
    </div>
  )
}

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

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const conversationId = searchParams.get('conversation') ?? ''
  const navigate = useNavigate()
  const [order, setOrder] = useState<Order | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [showRefund, setShowRefund] = useState(false)
  const [showCancel, setShowCancel] = useState(false)
  const [handoff, setHandoff] = useState<HandoffData | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!conversationId) return
    fetch(`/admin/api/conversations/${conversationId}/handoff`)
      .then((r) => r.json())
      .then((d) => { if (d) setHandoff(d) })
      .catch(() => {})
  }, [conversationId])

  const load = () => fetch(`/admin/api/orders/${id}`).then((r) => r.json()).then(setOrder)
  useEffect(() => { load() }, [id])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    if (menuOpen) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  if (!order) return <p>Loading...</p>

  const refundEligible = order.status === 'delivered' && !order.refund
  const cancelEligible = order.status === 'pending' || order.status === 'processing'
  const hasActions = refundEligible || cancelEligible

  return (
    <div>
      <button onClick={() => navigate('/admin')} style={{ marginBottom: 16 }}>← Back</button>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h2>Order #{order.id}</h2>

        {hasActions && (
          <div ref={menuRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setMenuOpen((o) => !o)}
              aria-haspopup="true"
              aria-expanded={menuOpen}
              style={{
                padding: '8px 16px',
                background: '#0066cc',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: 14,
              }}
            >
              Actions {menuOpen ? '▲' : '▾'}
            </button>

            {menuOpen && (
              <div
                role="menu"
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '110%',
                  background: '#fff',
                  border: '1px solid #ddd',
                  borderRadius: 8,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                  minWidth: 180,
                  zIndex: 10,
                  overflow: 'hidden',
                }}
              >
                {refundEligible && (
                  <button
                    role="menuitem"
                    onClick={() => { setMenuOpen(false); setShowRefund(true) }}
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '12px 16px',
                      border: 'none',
                      background: 'none',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontSize: 14,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#f5f5f5')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                  >
                    Issue Refund
                  </button>
                )}
                {cancelEligible && (
                  <button
                    role="menuitem"
                    onClick={() => { setMenuOpen(false); setShowCancel(true) }}
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '12px 16px',
                      border: 'none',
                      background: 'none',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontSize: 14,
                      color: '#cc0000',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#fff5f5')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                  >
                    Cancel Order
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <table style={{ borderCollapse: 'collapse', marginBottom: 24 }}>
        <tbody>
          <tr><td style={{ padding: '4px 16px 4px 0', fontWeight: 600 }}>Customer</td><td>{order.customerName} ({order.customerEmail})</td></tr>
          <tr><td style={{ padding: '4px 16px 4px 0', fontWeight: 600 }}>Status</td><td data-testid="order-status">{order.status}</td></tr>
          <tr><td style={{ padding: '4px 16px 4px 0', fontWeight: 600 }}>Total</td><td>${(order.totalCents / 100).toFixed(2)}</td></tr>
          <tr><td style={{ padding: '4px 16px 4px 0', fontWeight: 600 }}>Date</td><td>{new Date(order.createdAt).toLocaleDateString()}</td></tr>
        </tbody>
      </table>

      <h3>Items</h3>
      <ul>
        {order.items.map((item) => (
          <li key={item.id}>{item.productName} × {item.quantity} — ${(item.priceCents / 100).toFixed(2)}</li>
        ))}
      </ul>

      {order.refund && (
        <RefundDetailsCard refund={order.refund} orderTotal={order.totalCents} />
      )}

      {showRefund && (
        <RefundModal
          order={order}
          onClose={() => setShowRefund(false)}
          onSuccess={() => { setShowRefund(false); load() }}
        />
      )}
      {showCancel && (
        <CancelModal
          order={order}
          onClose={() => setShowCancel(false)}
          onSuccess={() => { setShowCancel(false); load() }}
        />
      )}

      {handoff && <EscalationHandoffCard handoff={handoff} />}
      {conversationId && <ActionLogTimeline conversationId={conversationId} />}
    </div>
  )
}