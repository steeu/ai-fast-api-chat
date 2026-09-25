<script lang="ts">
  import ChatWindow from './lib/components/ChatWindow.svelte'
</script>

<main>
  <header>
    <h1>AI Chat</h1>
  </header>
  <ChatWindow />
</main>

<style>
  main {
    display: flex;
    flex-direction: column;
    height: 100dvh;
    max-width: 800px;
    margin: 0 auto;
  }
  header {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
  }
  h1 {
    margin: 0;
    font-size: 1.2rem;
  }
</style>
