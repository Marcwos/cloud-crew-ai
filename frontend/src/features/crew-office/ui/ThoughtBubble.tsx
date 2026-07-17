interface ThoughtBubbleProps {
  message: string
}

export function ThoughtBubble({ message }: ThoughtBubbleProps) {
  return (
    <span className="thought-bubble" role="status">
      <span aria-hidden>💭</span> {message}
    </span>
  )
}
