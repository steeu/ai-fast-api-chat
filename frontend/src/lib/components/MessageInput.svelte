<script lang="ts">
  let {
    loading,
    onSend,
    onStop,
  }: { loading: boolean; onSend: (text: string) => void; onStop: () => void } = $props()

  let text = $state('')
  let textarea: HTMLTextAreaElement

  // Grow the textarea with its content (up to the max-height set in CSS)
  $effect(() => {
    text
    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  })

  function submit(event: SubmitEvent) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || loading) return
    onSend(trimmed)
    text = ''
  }

  // Enter sends, Shift+Enter inserts a new line
  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault()
      textarea.form?.requestSubmit()
    }
  }
</script>

<form onsubmit={submit}>
  <div class="composer">
    <textarea
      bind:this={textarea}
      bind:value={text}
      onkeydown={onKeydown}
      rows="1"
      placeholder="Nachricht eingeben…"
      aria-label="Nachricht"
    ></textarea>
    {#if loading}
      <button type="button" onclick={onStop} aria-label="Antwort stoppen" title="Stoppen">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2" /></svg>
      </button>
    {:else}
      <button type="submit" disabled={!text.trim()} aria-label="Senden" title="Senden">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 19V5M5 12l7-7 7 7" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    {/if}
  </div>
  <p class="hint">Enter zum Senden · Shift+Enter für neue Zeile</p>
</form>

<style>
  form {
    padding: 0 0 1rem;
  }
  .composer {
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
    padding: 0.5rem 0.5rem 0.5rem 1rem;
    border: 1px solid var(--border);
    border-radius: 24px;
    background: var(--surface);
    box-shadow: var(--shadow);
    transition: border-color 0.15s;
  }
  .composer:focus-within {
    border-color: var(--accent);
  }
  textarea {
    flex: 1;
    box-sizing: border-box;
    max-height: 200px;
    padding: 0.45rem 0;
    border: none;
    outline: none;
    resize: none;
    background: transparent;
    color: inherit;
    font: inherit;
    line-height: 1.5;
  }
  button {
    display: grid;
    place-items: center;
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    border: none;
    border-radius: 50%;
    background: var(--text);
    cursor: pointer;
    transition: opacity 0.15s;
  }
  button:disabled {
    opacity: 0.25;
    cursor: default;
  }
  svg {
    width: 18px;
    height: 18px;
    fill: var(--bg);
    stroke: var(--bg);
  }
  .hint {
    margin: 0.5rem 0 0;
    color: var(--muted);
    font-size: 0.75rem;
    text-align: center;
  }
</style>
