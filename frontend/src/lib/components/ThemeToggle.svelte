<script lang="ts">
  type Theme = 'dark' | 'light'

  // index.html already applied the saved theme before the first paint
  let theme = $state<Theme>(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark')

  function toggle() {
    theme = theme === 'dark' ? 'light' : 'dark'
    if (theme === 'light') document.documentElement.dataset.theme = 'light'
    else delete document.documentElement.dataset.theme
    try {
      localStorage.setItem('theme', theme)
    } catch {
      // Storage can be blocked (private mode); the toggle still works for this visit
    }
  }
</script>

<button
  type="button"
  onclick={toggle}
  aria-label={theme === 'dark' ? 'Helles Design aktivieren' : 'Dunkles Design aktivieren'}
  title={theme === 'dark' ? 'Helles Design' : 'Dunkles Design'}
>
  {#if theme === 'dark'}
    <!-- Sun -->
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
      />
    </svg>
  {:else}
    <!-- Moon -->
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
    </svg>
  {/if}
</button>

<style>
  button {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--border);
    border-radius: 50%;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }
  button:hover {
    background: var(--surface);
  }
  svg {
    width: 16px;
    height: 16px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
</style>
