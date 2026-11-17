interface GoogleIdentity {
  initialize(settings: {
    client_id: string
    callback: (response: { credential: string }) => void
    ux_mode: 'popup'
  }): void
  renderButton(element: HTMLElement, settings: {
    type: 'standard'
    text: 'signin_with'
    theme: 'outline'
    locale: string
  }): void
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdentity } }
  }
}

let loading: Promise<GoogleIdentity> | undefined

function load() {
  const loaded = window.google?.accounts.id
  if (loaded) return Promise.resolve(loaded)
  loading ??= new Promise<GoogleIdentity>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => {
      const identity = window.google?.accounts.id
      if (identity) resolve(identity)
      else reject(new Error('No pudimos preparar el acceso de Google.'))
    }
    script.onerror = () => reject(new Error('No pudimos conectar con Google.'))
    document.head.append(script)
  })
  return loading
}

export async function renderGoogleSignIn(container: HTMLElement, clientId: string,
                                         signIn: (credential: string) => void) {
  const identity = await load()
  if (!container.isConnected) return
  identity.initialize({
    client_id: clientId,
    callback: ({ credential }) => signIn(credential),
    ux_mode: 'popup',
  })
  identity.renderButton(container, { type: 'standard', text: 'signin_with', theme: 'outline', locale: 'es' })
}
