<script lang="ts">
  let { onPick }: { onPick: (text: string) => void } = $props()

  const suggestions = [
    'Erkläre mir FastAPI in drei Sätzen',
    'Schreib ein kurzes Gedicht über Kaffee',
    'Gib mir 5 Ideen für ein Wochenende',
    'Was ist der Unterschied zwischen REST und GraphQL?',
  ]
</script>

<div class="empty">
  <div class="logo" aria-hidden="true"></div>
  <h2>Wie kann ich dir helfen?</h2>
  <div class="suggestions">
    {#each suggestions as suggestion (suggestion)}
      <button type="button" onclick={() => onPick(suggestion)}>{suggestion}</button>
    {/each}
  </div>
</div>

<style>
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    min-height: 100%;
    padding: 2rem 0;
    text-align: center;
  }
  .logo {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: var(--accent-gradient);
  }
  h2 {
    margin: 0 0 0.5rem;
    font-size: 1.6rem;
    font-weight: 600;
    letter-spacing: -0.02em;
  }
  .suggestions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.6rem;
    width: 100%;
  }
  button {
    padding: 0.8rem 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: inherit;
    font: inherit;
    font-size: 0.9rem;
    text-align: left;
    cursor: pointer;
    transition:
      border-color 0.15s,
      background 0.15s;
  }
  button:hover {
    border-color: var(--accent);
    background: var(--surface-hover);
  }
</style>
