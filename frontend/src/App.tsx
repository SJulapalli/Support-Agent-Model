import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Chat from './pages/Chat'
import OrderTable from './components/admin/OrderTable'
import OrderDetail from './components/admin/OrderDetail'
import ConversationList from './components/admin/ConversationList'
import ConversationDetail from './components/admin/ConversationDetail'
import AdminLayout from './components/admin/AdminLayout'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/admin" element={<AdminLayout><OrderTable /></AdminLayout>} />
        <Route path="/admin/orders/:id" element={<AdminLayout><OrderDetail /></AdminLayout>} />
        <Route path="/admin/conversations" element={<AdminLayout><ConversationList /></AdminLayout>} />
        <Route path="/admin/conversations/:id" element={<AdminLayout><ConversationDetail /></AdminLayout>} />
      </Routes>
    </BrowserRouter>
  )
}
