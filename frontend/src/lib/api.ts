export type Role = 'user' | 'assistant'

export interface ChatMessage {
  role: Role
  content: string
}

export interface StreamHandlers {
  onToken: (text: string) => void
  signal?: AbortSignal
}

// Later: set this after login (e.g. from an auth provider), it is sent as Bearer token
let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

/**
 * Sends the conversation to the backend and calls onToken for every streamed text piece.
 * The backend answers with Server-Sent Events. Since we use POST, EventSource can't be used,
 * so the stream is read and parsed manually.
 */
export async function streamChat(messages: ChatMessage[], { onToken, signal }: StreamHandlers) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({ messages }),
    signal,
  })
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : ''
    throw new Error(detail || `Request failed (${response.status})`)
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value

    // SSE events are separated by a blank line
    let boundary: number
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      const { event, data } = parseEvent(block)
      if (event === 'token') onToken(data)
      else if (event === 'error') throw new Error(data)
      else if (event === 'done') return
    }
  }
}

function parseEvent(block: string): { event: string; data: string } {
  let event = 'message'
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  // The backend JSON-encodes data, so newlines inside tokens survive the transport
  return { event, data: data ? JSON.parse(data) : '' }
}
