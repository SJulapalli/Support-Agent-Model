import { useState, useRef, useEffect } from 'react'
import { useChat } from '../../hooks/useChat'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'

export default function ChatWidget() {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const { messages, status, sendMessage } = useChat()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || status === 'streaming' || status === 'agent_working') return
    sendMessage(input.trim())
    setInput('')
  }

  return (
    <div style={{ width: 420, height: 600, display: 'flex', flexDirection: 'column', border: '1px solid #ddd', borderRadius: 12, background: '#fff', overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #eee', fontWeight: 600 }}>
        NorthShop Support
        {status === 'escalated' && (
          <span style={{ marginLeft: 8, fontSize: 12, color: '#888', fontWeight: 400 }}>
            Transferred to human support
          </span>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {(status === 'streaming' || status === 'agent_working') && (
          <TypingIndicator agentWorking={status === 'agent_working'} />
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} style={{ padding: 12, borderTop: '1px solid #eee', display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={status === 'escalated'}
          style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', outline: 'none' }}
        />
        <button
          type="submit"
          disabled={!input.trim() || status === 'streaming' || status === 'agent_working' || status === 'escalated'}
          style={{ padding: '8px 16px', borderRadius: 8, background: '#0066ff', color: '#fff', border: 'none', cursor: 'pointer' }}
        >
          Send
        </button>
      </form>
    </div>
  )
}
