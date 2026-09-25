import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    // During development, forward API calls to the FastAPI backend
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
