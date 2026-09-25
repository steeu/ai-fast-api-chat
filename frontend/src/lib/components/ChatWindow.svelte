<script lang="ts">
  import { streamChat, type ChatMessage } from '../api'
  import MessageInput from './MessageInput.svelte'
  import MessageList from './MessageList.svelte'

  let messages = $state<ChatMessage[]>([])
  let loading = $state(false)
  let error = $state<string | null>(null)
  let controller: AbortController | null = null

  async function send(text: string) {
    error = null
    messages.push({ role: 'user', content: text })
    // Snapshot of the conversation to send, without the empty assistant placeholder
    const history = $state.snapshot(messages)
    messages.push({ role: 'assistant', content: '' })
    const answer = messages[messages.length - 1]

    loading = true
    controller = new AbortController()
    try {
      await streamChat(history, {
        onToken: (token) => (answer.content += token),
        signal: controller.signal,
      })
    } catch (e) {
      if (!(e instanceof DOMException && e.name === 'AbortError')) {
        error = e instanceof Error ? e.message : String(e)
      }
    } finally {
      // Drop an assistant message that never got any content
      if (!answer.content) messages.pop()
      loading = false
      controller = null
    }
  }

  function stop() {
    controller?.abort()
  }
</script>

<div class="chat">
  <MessageList {messages} {loading} />
  {#if error}
    <p class="error">{error}</p>
  {/if}
  <MessageInput {loading} onSend={send} onStop={stop} />
</div>

<style>
  .chat {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .error {
    margin: 0 1rem;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    background: var(--error-bg);
    color: var(--error);
  }
</style>
