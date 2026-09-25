<script lang="ts">
  let {
    loading,
    onSend,
    onStop,
  }: { loading: boolean; onSend: (text: string) => void; onStop: () => void } = $props()

  let text = $state('')

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
      ;(event.currentTarget as HTMLTextAreaElement).form?.requestSubmit()
    }
  }
</script>

<form onsubmit={submit}>
  <textarea bind:value={text} onkeydown={onKeydown} rows="2" placeholder="Nachricht eingeben…"
  ></textarea>
  {#if loading}
    <button type="button" onclick={onStop}>Stopp</button>
  {:else}
    <button type="submit" disabled={!text.trim()}>Senden</button>
  {/if}
</form>

<style>
  form {
    display: flex;
    gap: 0.5rem;
    padding: 1rem;
    border-top: 1px solid var(--border);
  }
  textarea {
    flex: 1;
    resize: none;
    padding: 0.6rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    font: inherit;
    background: var(--bg);
    color: inherit;
  }
  button {
    padding: 0 1.2rem;
    border: none;
    border-radius: 8px;
    background: var(--accent);
    color: white;
    font: inherit;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
