import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Chat from './pages/Chat'
import OrderTable from './components/admin/OrderTable'
import OrderDetail from './components/admin/OrderDetail'
import AdminLayout from './components/admin/AdminLayout'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/admin" element={<AdminLayout><OrderTable /></AdminLayout>} />
        <Route path="/admin/orders/:id" element={<AdminLayout><OrderDetail /></AdminLayout>} />
      </Routes>
    </BrowserRouter>
  )
}
