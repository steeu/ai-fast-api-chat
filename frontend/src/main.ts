import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'
import { initAuth } from './lib/auth'

const target = document.getElementById('app')!

async function start() {
  try {
    // Without a session the browser is redirected to the login page and the app isn't mounted
    if (!(await initAuth())) return
  } catch (e) {
    console.error(e)
    target.innerHTML =
      '<p class="startup-error">Anmeldung fehlgeschlagen. <a href="/">Erneut versuchen</a></p>'
    return
  }
  mount(App, { target })
}

start()
