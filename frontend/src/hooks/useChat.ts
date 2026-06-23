import { useState, useCallback } from 'react'
import { Message, ChatStatus } from '../types'

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [conversationId] = useState(() => crypto.randomUUID())

  const sendMessage = useCallback(async (content: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      createdAt: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setStatus('streaming')

    const assistantId = crypto.randomUUID()
    setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '', createdAt: new Date() }])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, message: content }),
      })

      if (!response.body) throw new Error('No response body')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter((l) => l.startsWith('data: '))

        for (const line of lines) {
          const data = JSON.parse(line.slice(6))

          if (data.type === 'text') {
            setMessages((prev) =>
              prev.map((m) => m.id === assistantId ? { ...m, content: m.content + data.content } : m)
            )
          } else if (data.type === 'status') {
            setStatus(data.status)
          } else if (data.type === 'done') {
            setStatus('idle')
          }
        }
      }
    } catch (err) {
      console.error(err)
      setStatus('idle')
    }
  }, [conversationId])

  return { messages, status, sendMessage }
}
