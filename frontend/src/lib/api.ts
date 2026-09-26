export type Role = 'user' | 'assistant'

export interface Usage {
  model: string
  input_tokens: number
  cached_tokens: number
  output_tokens: number
  reasoning_tokens: number
  // Estimated cost in CHF, null if the model has no known price
  cost_chf: number | null
}

export interface ChatMessage {
  role: Role
  content: string
  usage?: Usage
}

export interface StreamHandlers {
  onToken: (text: string) => void
  onUsage?: (usage: Usage) => void
  signal?: AbortSignal
}

/** HTTP error before streaming started; status lets the UI react to 401/403. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

// Set by lib/auth.ts after login and on every token renewal, sent as Bearer token
let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

/**
 * Sends the conversation to the backend and calls onToken for every streamed text piece.
 * The backend answers with Server-Sent Events. Since we use POST, EventSource can't be used,
 * so the stream is read and parsed manually.
 */
export async function streamChat(
  messages: ChatMessage[],
  { onToken, onUsage, signal }: StreamHandlers,
) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers,
    // Only role and content are part of the request, usage stays in the browser
    body: JSON.stringify({ messages: messages.map(({ role, content }) => ({ role, content })) }),
    signal,
  })
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : ''
    throw new ApiError(detail || `Request failed (${response.status})`, response.status)
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
      else if (event === 'usage') onUsage?.(data)
      else if (event === 'error') throw new Error(data)
      else if (event === 'done') return
    }
  }
}

// data is JSON: a string for token/error, an object for usage
function parseEvent(block: string): { event: string; data: any } {
  let event = 'message'
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  // The backend JSON-encodes data, so newlines inside tokens survive the transport
  return { event, data: data ? JSON.parse(data) : '' }
}
