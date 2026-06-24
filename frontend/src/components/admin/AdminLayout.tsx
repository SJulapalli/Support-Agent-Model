import { useNavigate, useLocation } from 'react-router-dom'

interface Props {
  children: React.ReactNode
}

export default function AdminLayout({ children }: Props) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const isOrders = pathname === '/admin' || pathname.startsWith('/admin/orders')
  const isConversations = pathname.startsWith('/admin/conversations')

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px',
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    borderBottom: active ? '2px solid #0066cc' : '2px solid transparent',
    color: active ? '#0066cc' : '#555',
    fontWeight: active ? 600 : 400,
    fontSize: 14,
    marginBottom: -2,
  })

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 24 }}>
      <h1 style={{ marginBottom: 8 }}>ShopAdmin — NorthShop Internal Portal</h1>
      <nav style={{ display: 'flex', gap: 4, borderBottom: '2px solid #eee', marginBottom: 24 }}>
        <button style={tabStyle(isOrders)} onClick={() => navigate('/admin')}>Orders</button>
        <button style={tabStyle(isConversations)} onClick={() => navigate('/admin/conversations')}>Conversations</button>
      </nav>
      {children}
    </div>
  )
}