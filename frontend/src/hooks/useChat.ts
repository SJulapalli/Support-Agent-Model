import { useState, useCallback, useRef, useEffect } from 'react'
import { Message, ChatStatus } from '../types'

export interface ActionLogEvent {
  event_type: string
  payload: Record<string, unknown>
}

export interface HandoffCard {
  reason?: string
  customer?: string
  orders_reviewed?: string[]
  actions_attempted?: string[]
  sentiment?: string
  recommended_next_step?: string
}

const CHARS_PER_MS = 13 / 1000 // ≈150 wpm = 13 chars/sec

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [isEscalated, setIsEscalated] = useState(false)
  const [handoffCard, setHandoffCard] = useState<HandoffCard | null>(null)
  const [actionLog, setActionLog] = useState<ActionLogEvent[]>([])
  const [conversationId] = useState(() => crypto.randomUUID())

  // Pacing queue: buffer tokens, drain at ~13 chars/sec
  const tokenQueueRef = useRef<string>('')
  const displayedRef = useRef<string>('')
  const pacingRef = useRef<NodeJS.Timeout | null>(null)
  const currentAssistantIdRef = useRef<string | null>(null)
  const skipRef = useRef(false)

  const _startPacing = useCallback((assistantId: string) => {
    if (pacingRef.current) return
    pacingRef.current = setInterval(() => {
      if (skipRef.current) {
        // Flush entire queue instantly
        const remaining = tokenQueueRef.current
        tokenQueueRef.current = ''
        displayedRef.current += remaining
        setMessages((prev) =>
          prev.map((m) => m.id === assistantId ? { ...m, content: displayedRef.current } : m)
        )
        skipRef.current = false
        clearInterval(pacingRef.current!)
        pacingRef.current = null
        return
      }

      const charsThisTick = Math.max(1, Math.round(CHARS_PER_MS * 16)) // ~16ms tick
      const chunk = tokenQueueRef.current.slice(0, charsThisTick)
      tokenQueueRef.current = tokenQueueRef.current.slice(charsThisTick)
      if (chunk) {
        displayedRef.current += chunk
        setMessages((prev) =>
          prev.map((m) => m.id === assistantId ? { ...m, content: displayedRef.current } : m)
        )
      }
      if (tokenQueueRef.current === '' && chunk === '') {
        clearInterval(pacingRef.current!)
        pacingRef.current = null
      }
    }, 16)
  }, [])

  const _stopPacing = useCallback(() => {
    if (pacingRef.current) {
      clearInterval(pacingRef.current)
      pacingRef.current = null
    }
  }, [])

  // Expose skip function for click handler
  const skipPacing = useCallback(() => {
    skipRef.current = true
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      createdAt: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setStatus('streaming')
    setActionLog([])

    const assistantId = crypto.randomUUID()
    currentAssistantIdRef.current = assistantId
    tokenQueueRef.current = ''
    displayedRef.current = ''
    skipRef.current = false
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
            // Queue tokens for paced delivery
            tokenQueueRef.current += data.content
            _startPacing(assistantId)
          } else if (data.type === 'correction') {
            // Replace remaining queue with corrected text, reset display
            _stopPacing()
            const corrected: string = data.content
            tokenQueueRef.current = corrected
            displayedRef.current = ''
            _startPacing(assistantId)
          } else if (data.type === 'action_log') {
            // Not paced — display immediately
            setActionLog((prev) => [...prev, data.content as ActionLogEvent])
          } else if (data.type === 'handoff') {
            setHandoffCard(data.content as HandoffCard)
          } else if (data.type === 'status') {
            if (data.content === 'escalated') {
              setIsEscalated(true)
            }
            setStatus(data.content as ChatStatus)
          } else if (data.type === 'done') {
            setStatus('idle')
          }
        }
      }
    } catch (err) {
      console.error(err)
      setStatus('idle')
    }
  }, [conversationId, _startPacing, _stopPacing])

  // Clean up pacing interval on unmount
  useEffect(() => {
    return () => { _stopPacing() }
  }, [_stopPacing])

  return { messages, status, isEscalated, handoffCard, actionLog, conversationId, sendMessage, skipPacing }
}
