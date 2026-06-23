interface Props {
  agentWorking: boolean
}

export default function TypingIndicator({ agentWorking }: Props) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#888', fontSize: 13 }}>
      <span>{agentWorking ? 'Agent working...' : 'Typing...'}</span>
    </div>
  )
}
