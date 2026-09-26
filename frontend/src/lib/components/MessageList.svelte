<script lang="ts">
  import type { ChatMessage } from '../api'
  import { renderMarkdown } from '../markdown'
  import { formatUsage } from '../usage'

  let { messages, loading }: { messages: ChatMessage[]; loading: boolean } = $props()
</script>

<div class="thread">
  {#each messages as message, i (i)}
    {#if message.role === 'user'}
      <div class="message user">{message.content}</div>
    {:else}
      <div class="message assistant">
        {#if message.content}
          <div class="markdown">{@html renderMarkdown(message.content)}</div>
        {:else if loading && i === messages.length - 1}
          <div class="typing" aria-label="Antwort wird geschrieben">
            <span></span><span></span><span></span>
          </div>
        {/if}
        {#if message.usage}
          <div class="meta" title="Geschätzte Kosten, ohne Gewähr">{formatUsage(message.usage)}</div>
        {/if}
      </div>
    {/if}
  {/each}
</div>

<style>
  .thread {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    padding: 1.5rem 0;
  }
  .message {
    animation: appear 0.2s ease-out;
    line-height: 1.6;
    overflow-wrap: anywhere;
  }
  .user {
    align-self: flex-end;
    max-width: 80%;
    padding: 0.65rem 1rem;
    border-radius: 18px 18px 4px 18px;
    background: var(--user-bubble);
    white-space: pre-wrap;
  }
  .assistant {
    align-self: stretch;
  }

  /* Markdown content ({@html} needs :global for inner elements) */
  .markdown :global(:first-child) {
    margin-top: 0;
  }
  .markdown :global(:last-child) {
    margin-bottom: 0;
  }
  .markdown :global(p),
  .markdown :global(ul),
  .markdown :global(ol) {
    margin: 0 0 0.75rem;
  }
  .markdown :global(h1),
  .markdown :global(h2),
  .markdown :global(h3) {
    margin: 1.25rem 0 0.5rem;
    line-height: 1.3;
    letter-spacing: -0.01em;
  }
  .markdown :global(h1) {
    font-size: 1.35rem;
  }
  .markdown :global(h2) {
    font-size: 1.2rem;
  }
  .markdown :global(h3) {
    font-size: 1.05rem;
  }
  .markdown :global(li + li) {
    margin-top: 0.25rem;
  }
  .markdown :global(a) {
    color: var(--accent);
  }
  .markdown :global(code) {
    padding: 0.1em 0.35em;
    border-radius: 5px;
    background: var(--surface);
    font-family: var(--font-mono);
    font-size: 0.88em;
  }
  .markdown :global(pre) {
    margin: 0 0 0.75rem;
    padding: 0.9rem 1rem;
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .markdown :global(pre code) {
    padding: 0;
    background: none;
  }
  .markdown :global(blockquote) {
    margin: 0 0 0.75rem;
    padding-left: 1rem;
    border-left: 3px solid var(--border);
    color: var(--muted);
  }
  .markdown :global(table) {
    border-collapse: collapse;
    margin-bottom: 0.75rem;
  }
  .markdown :global(th),
  .markdown :global(td) {
    padding: 0.4rem 0.7rem;
    border: 1px solid var(--border);
  }

  .meta {
    margin-top: 0.5rem;
    color: var(--muted);
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
  }

  .typing {
    display: flex;
    gap: 5px;
    padding: 0.5rem 0;
  }
  .typing span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--muted);
    animation: bounce 1.2s infinite ease-in-out;
  }
  .typing span:nth-child(2) {
    animation-delay: 0.15s;
  }
  .typing span:nth-child(3) {
    animation-delay: 0.3s;
  }

  @keyframes appear {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
  }
  @keyframes bounce {
    0%,
    60%,
    100% {
      opacity: 0.4;
      transform: translateY(0);
    }
    30% {
      opacity: 1;
      transform: translateY(-4px);
    }
  }
</style>
