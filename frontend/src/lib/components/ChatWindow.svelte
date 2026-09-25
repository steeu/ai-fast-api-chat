<script lang="ts">
  import { tick } from 'svelte'
  import { streamChat, type ChatMessage } from '../api'
  import EmptyState from './EmptyState.svelte'
  import MessageInput from './MessageInput.svelte'
  import MessageList from './MessageList.svelte'
  import ThemeToggle from './ThemeToggle.svelte'

  let messages = $state<ChatMessage[]>([])
  let loading = $state(false)
  let error = $state<string | null>(null)
  let controller: AbortController | null = null

  let scroller: HTMLElement
  // Only auto-scroll while the user is at the bottom, so they can scroll up during streaming
  let stickToBottom = true

  function onScroll() {
    stickToBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 80
  }

  $effect(() => {
    messages.at(-1)?.content
    if (stickToBottom) scroller.scrollTo({ top: scroller.scrollHeight })
  })

  async function send(text: string) {
    error = null
    stickToBottom = true
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

  async function newChat() {
    stop()
    await tick()
    messages = []
    error = null
  }
</script>

<div class="chat">
  <header>
    <div class="brand">
      <span class="logo" class:active={loading} aria-hidden="true"></span>
      AI
    </div>
    <div class="actions">
      {#if messages.length > 0}
        <button type="button" class="new-chat" onclick={newChat}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 5v14M5 12h14" fill="none" stroke-width="2" stroke-linecap="round" />
          </svg>
          Neuer Chat
        </button>
      {/if}
      <ThemeToggle />
    </div>
  </header>

  <div class="scroller" bind:this={scroller} onscroll={onScroll}>
    <div class="column">
      {#if messages.length === 0}
        <EmptyState onPick={send} />
      {:else}
        <MessageList {messages} {loading} />
      {/if}
    </div>
  </div>

  <div class="column">
    {#if error}
      <div class="error" role="alert">
        <span>{error}</span>
        <button type="button" onclick={() => (error = null)} aria-label="Schliessen">×</button>
      </div>
    {/if}
    <MessageInput {loading} onSend={send} onStop={stop} />
  </div>
</div>

<style>
  .chat {
    display: flex;
    flex-direction: column;
    height: 100dvh;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-weight: 600;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  /* Gradient flows continuously; while an answer streams, the logo also spins */
  .logo {
    width: 22px;
    height: 22px;
    border-radius: 7px;
    background: var(--accent-gradient);
    background-size: 300% 300%;
    animation: flow 6s ease-in-out infinite;
  }
  .logo.active {
    animation:
      flow 1.5s ease-in-out infinite,
      spin 1.4s ease-in-out infinite;
  }
  @keyframes flow {
    0%,
    100% {
      background-position: 0% 50%;
    }
    50% {
      background-position: 100% 50%;
    }
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .new-chat {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.8rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 0.85rem;
    cursor: pointer;
  }
  .new-chat:hover {
    background: var(--surface);
  }
  .new-chat svg {
    width: 14px;
    height: 14px;
    stroke: currentColor;
  }
  .scroller {
    flex: 1;
    overflow-y: auto;
  }
  /* Centered reading column; the scroller itself stays full width */
  .column {
    width: 100%;
    max-width: 760px;
    margin: 0 auto;
    padding: 0 1rem;
    box-sizing: border-box;
  }
  .scroller .column {
    min-height: 100%;
  }
  .error {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    padding: 0.6rem 0.9rem;
    border: 1px solid var(--error-border);
    border-radius: var(--radius);
    background: var(--error-bg);
    color: var(--error);
    font-size: 0.9rem;
  }
  .error button {
    border: none;
    background: none;
    color: inherit;
    font-size: 1.2rem;
    line-height: 1;
    cursor: pointer;
  }
</style>
