import { useEffect, useRef, useState } from 'react'

interface ChallengeDialogProps {
  open: boolean
  isRunning: boolean
  error: string | null
  onClose: () => void
  onSubmit: (challenge: string) => void
}

/** Pixel-style briefing dialogue, opened by interacting with Leslie. */
export function ChallengeDialog({
  open,
  isRunning,
  error,
  onClose,
  onSubmit,
}: ChallengeDialogProps) {
  const [challenge, setChallenge] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!open) return
    textareaRef.current?.focus()
  }, [open])

  if (!open) return null

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = challenge.trim()
    if (!trimmed || isRunning) return
    onSubmit(trimmed)
  }

  return (
    <div className="challenge-dialog-backdrop" role="presentation">
      <form className="challenge-dialog" onSubmit={submit} aria-label="New crew mission">
        <button
          type="button"
          className="challenge-dialog-close"
          onClick={onClose}
          aria-label="Close mission dialogue"
          disabled={isRunning}
        >
          ×
        </button>
        <p className="challenge-dialog-kicker">LESLIE · ORCHESTRATOR</p>
        <h1>¿Qué misión necesita la crew?</h1>
        <textarea
          ref={textareaRef}
          value={challenge}
          onChange={(event) => setChallenge(event.target.value)}
          placeholder="Ej.: Diseña una plataforma de ecommerce escalable y segura."
          rows={4}
          disabled={isRunning}
        />
        {error && <p className="challenge-dialog-error">{error}</p>}
        <button className="challenge-dialog-submit" type="submit" disabled={!challenge.trim() || isRunning}>
          {isRunning ? 'La crew está trabajando…' : 'Asignar misión'}
        </button>
      </form>
    </div>
  )
}
