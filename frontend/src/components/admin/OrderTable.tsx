import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Order } from '../../types'

export default function OrderTable() {
  const [orders, setOrders] = useState<Order[]>([])
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams()
    const trimmed = search.trim()
    if (trimmed) {
      // Heuristic: if it contains @ treat as email, otherwise name
      if (trimmed.includes('@')) {
        params.set('email', trimmed)
      } else {
        params.set('name', trimmed)
      }
    }
    const query = params.toString() ? `?${params}` : ''
    fetch(`/admin/api/orders${query}`).then((r) => r.json()).then(setOrders)
  }, [search])

  return (
    <div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by customer name or email"
        data-testid="customer-search"
        style={{ marginTop: 24, marginBottom: 12, padding: '8px 12px', width: 360, borderRadius: 6, border: '1px solid #ddd' }}
      />
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #eee', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>Order ID</th>
            <th style={{ padding: 8 }}>Customer</th>
            <th style={{ padding: 8 }}>Status</th>
            <th style={{ padding: 8 }}>Total</th>
            <th style={{ padding: 8 }}>Date</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr
              key={order.id}
              data-testid={`order-row-${order.id}`}
              onClick={() => navigate(`/admin/orders/${order.id}`)}
              style={{ borderBottom: '1px solid #eee', cursor: 'pointer' }}
            >
              <td style={{ padding: 8 }}>#{order.id}</td>
              <td style={{ padding: 8 }}>{order.customerName}</td>
              <td style={{ padding: 8 }}>{order.status}</td>
              <td style={{ padding: 8 }}>${(order.totalCents / 100).toFixed(2)}</td>
              <td style={{ padding: 8 }}>{new Date(order.createdAt).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
