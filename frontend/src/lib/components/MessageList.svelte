<script lang="ts">
  import type { ChatMessage } from '../api'

  let { messages, loading }: { messages: ChatMessage[]; loading: boolean } = $props()

  let container: HTMLElement

  // Keep the newest message in view while tokens stream in
  $effect(() => {
    messages.at(-1)?.content
    container?.scrollTo({ top: container.scrollHeight })
  })
</script>

<section class="messages" bind:this={container}>
  {#if messages.length === 0}
    <p class="empty">Stell eine Frage, um zu starten.</p>
  {/if}
  {#each messages as message, i (i)}
    <div class="message {message.role}">
      {#if message.content}
        {message.content}
      {:else if loading && i === messages.length - 1}
        <span class="typing">…</span>
      {/if}
    </div>
  {/each}
</section>

<style>
  .messages {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
  }
  .empty {
    margin: auto;
    color: var(--muted);
  }
  .message {
    max-width: 80%;
    padding: 0.6rem 0.9rem;
    border-radius: 12px;
    white-space: pre-wrap;
    line-height: 1.5;
  }
  .user {
    align-self: flex-end;
    background: var(--accent);
    color: white;
  }
  .assistant {
    align-self: flex-start;
    background: var(--surface);
  }
  .typing {
    color: var(--muted);
  }
</style>
