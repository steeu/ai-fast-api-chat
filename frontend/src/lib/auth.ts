import { UserManager, type User } from 'oidc-client-ts'
import { setAuthToken } from './api'

interface AuthConfig {
  enabled: boolean
  issuer: string | null
  client_id: string | null
  project_id: string | null
}

let manager: UserManager | null = null
let userName: string | null = null
let firstName: string | null = null

/**
 * Runs before the app is mounted. Returns true when the app may start, false when the browser
 * is being redirected to the Zitadel login page. Without AUTH_ENABLED it does nothing.
 */
export async function initAuth(): Promise<boolean> {
  const response = await fetch('/api/auth/config')
  if (!response.ok) throw new Error(`Auth config failed (${response.status})`)
  const config: AuthConfig = await response.json()
  if (!config.enabled) return true

  // Must match the redirect URIs registered in Zitadel exactly (no trailing slash)
  const origin = window.location.origin
  manager = new UserManager({
    authority: config.issuer!,
    client_id: config.client_id!,
    redirect_uri: origin,
    post_logout_redirect_uri: origin,
    // offline_access: refresh token for silent renewal; :aud puts the project into the token audience
    scope: `openid profile email offline_access urn:zitadel:iam:org:project:id:${config.project_id}:aud`,
  })
  // Renewals (automaticSilentRenew is on by default) must reach the API client. If a renewal
  // fails, the next request gets a 401 and ChatWindow sends the user to the login page.
  manager.events.addUserLoaded((user) => useUser(user))

  // Coming back from Zitadel: exchange the code (PKCE) for tokens, then clean up the URL
  const params = new URLSearchParams(window.location.search)
  if (params.has('state') && (params.has('code') || params.has('error'))) {
    await manager.signinRedirectCallback()
    window.history.replaceState(null, '', window.location.pathname)
  }

  let user = await manager.getUser()
  if (user?.expired && user.refresh_token) {
    user = await manager.signinSilent().catch(() => null)
  }
  if (!user || user.expired) {
    await signIn()
    return false
  }
  useUser(user)
  return true
}

function useUser(user: User) {
  setAuthToken(user.access_token)
  const profile = user.profile
  userName = profile.name ?? profile.preferred_username ?? profile.email ?? null
  // For the greeting; login names or emails would read oddly, so only real names are used
  firstName = profile.given_name ?? profile.name?.split(' ')[0] ?? null
}

/** First name for a personal greeting, null without login or name. */
export function currentFirstName(): string | null {
  return firstName
}

/** Display name of the signed-in user, null without login. */
export function currentUserName(): string | null {
  return userName
}

export function isAuthEnabled(): boolean {
  return manager !== null
}

export async function signIn() {
  await manager?.signinRedirect()
}

export async function signOut() {
  await manager?.signoutRedirect()
}
