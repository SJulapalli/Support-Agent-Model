import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Order } from '../../types'

const ORDER_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'refunded', 'cancelled']

export default function OrderTable() {
  const [orders, setOrders] = useState<Order[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams()
    const trimmed = search.trim()
    if (trimmed) {
      if (trimmed.includes('@')) {
        params.set('email', trimmed)
      } else {
        params.set('name', trimmed)
      }
    }
    if (statusFilter) params.set('status', statusFilter)
    const query = params.toString() ? `?${params}` : ''
    fetch(`/admin/api/orders${query}`).then((r) => r.json()).then(setOrders)
  }, [search, statusFilter])

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== 'Enter') return
    const m = search.trim().match(/^#?(\d+)$/)
    if (m) navigate(`/admin/orders/${m[1]}`)
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginTop: 24, marginBottom: 12, alignItems: 'center' }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search by name, email, or order #ID (Enter to jump)"
          data-testid="customer-search"
          style={{ padding: '8px 12px', width: 360, borderRadius: 6, border: '1px solid #ddd' }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Status"
          style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', background: '#fff' }}
        >
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
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
