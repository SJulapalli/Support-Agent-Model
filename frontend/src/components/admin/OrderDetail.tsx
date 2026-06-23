import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Order } from '../../types'
import RefundModal from './RefundModal'

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [order, setOrder] = useState<Order | null>(null)
  const [showRefund, setShowRefund] = useState(false)

  const load = () => fetch(`/admin/api/orders/${id}`).then((r) => r.json()).then(setOrder)

  useEffect(() => { load() }, [id])

  if (!order) return <p>Loading...</p>

  const refundEligible = order.status === 'delivered' && !order.refund

  return (
    <div>
      <button onClick={() => navigate('/admin')} style={{ marginBottom: 16 }}>← Back</button>
      <h2>Order #{order.id}</h2>

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

      {order.refund ? (
        <p style={{ color: 'green' }}>Refund issued: ${(order.refund.amountCents / 100).toFixed(2)} ({order.refund.status})</p>
      ) : refundEligible ? (
        <button
          onClick={() => setShowRefund(true)}
          data-testid="issue-refund-btn"
          style={{ marginTop: 16, padding: '10px 20px', background: '#cc0000', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
        >
          Issue Refund
        </button>
      ) : (
        <p style={{ color: '#888' }}>Not eligible for refund</p>
      )}

      {showRefund && (
        <RefundModal order={order} onClose={() => setShowRefund(false)} onSuccess={() => { setShowRefund(false); load() }} />
      )}
    </div>
  )
}
