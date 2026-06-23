interface Props {
  children: React.ReactNode
}

export default function AdminLayout({ children }: Props) {
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 24 }}>
      <h1>ShopAdmin — NorthShop Internal Portal</h1>
      {children}
    </div>
  )
}
