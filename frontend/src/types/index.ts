export type Role = 'user' | 'assistant'

export interface Message {
  id: string
  role: Role
  content: string
  createdAt: Date
}

export type ChatStatus = 'idle' | 'streaming' | 'agent_working' | 'escalated'

export interface Order {
  id: number
  customerId: number
  customerName: string
  customerEmail: string
  status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'refunded' | 'cancelled'
  totalCents: number
  createdAt: string
  items: OrderItem[]
  refund?: Refund
}

export interface OrderItem {
  id: number
  productName: string
  quantity: number
  priceCents: number
}

export interface Refund {
  id: number
  orderId: number
  amountCents: number
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
}

export interface Customer {
  id: number
  name: string
  email: string
  createdAt: string
}
