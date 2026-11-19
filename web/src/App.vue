<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Capacitor } from '@capacitor/core'
import { GraduationCap } from '@lucide/vue'
import type { Account } from './client'
import { api, errorText, RequestError } from './client'
import SignIn from './SignIn.vue'
import Community from './Community.vue'
import ConnectionStatus from './ConnectionStatus.vue'
import { rememberedSessionKey, SessionStore } from './sessionStorage'

const token = ref('')
const account = ref<Account | null>(null)
const busy = ref(false)
const message = ref('')
const native = Capacitor.isNativePlatform()
const store = new SessionStore(() => window.sessionStorage, () => window.localStorage)
const initial = store.read()
const saved = ref(initial.token)
const remember = ref(initial.remembered)
const storageNotice = ref('')
const restoring = ref(Boolean(saved.value))
const roleNames = { student: 'Estudiante', faculty: 'Docente', admin: 'Administración', staff: 'Personal' }
let sessionRevision = 0

function setSession(value: string, user: Account, loginPreference?: boolean) {
  token.value = value
  account.value = user
  saved.value = value
  if (loginPreference === undefined) store.cacheInTab(value)
  else {
    remember.value = store.saveLogin(value, loginPreference)
    storageNotice.value = loginPreference && !remember.value
      ? 'Este dispositivo no permitió conservar la sesión para otra apertura. Puedes continuar en esta pantalla.' : ''
  }
}

async function restore() {
  if (!saved.value) return
  const revision = ++sessionRevision
  const credential = saved.value
  restoring.value = true
  message.value = ''
  try {
    const user = await api<Account>('/session', { token: credential })
    if (revision === sessionRevision) setSession(credential, user)
  } catch (error) {
    if (revision !== sessionRevision) return
    if (error instanceof RequestError && error.status === 401) clearSession('La sesión terminó. Vuelve a ingresar.')
    else message.value = errorText(error)
  } finally {
    if (revision === sessionRevision) restoring.value = false
  }
}
function sessionChanged(event: StorageEvent) {
  const current = token.value || saved.value
  if (event.key === rememberedSessionKey && current && event.oldValue === current && event.newValue === null) {
    clearSession('La sesión se cerró en otra pestaña. Vuelve a ingresar.')
  }
}
onMounted(() => {
  window.addEventListener('storage', sessionChanged)
  void restore()
})
onBeforeUnmount(() => window.removeEventListener('storage', sessionChanged))

async function signIn(credential: string) {
  if (busy.value) return
  const revision = ++sessionRevision
  const keep = remember.value
  busy.value = true
  message.value = ''
  try {
    const session = await api<{ token: string; account: Account }>('/session', {
      method: 'POST', data: { credential },
    })
    if (revision === sessionRevision) setSession(session.token, session.account, keep)
  } catch (error) {
    if (revision === sessionRevision) message.value = errorText(error)
  } finally {
    if (revision === sessionRevision) busy.value = false
  }
}

function clearSession(notice = '') {
  store.clear(token.value || saved.value)
  sessionRevision++
  busy.value = false
  restoring.value = false
  token.value = ''
  account.value = null
  saved.value = ''
  remember.value = false
  storageNotice.value = ''
  message.value = notice
}

function sessionExpired(expiredToken: string) {
  if (expiredToken === token.value) clearSession('La sesión terminó. Vuelve a ingresar.')
}

async function signOut() {
  const current = token.value || saved.value
  clearSession()
  try {
    await api('/session', { token: current, method: 'DELETE' })
  } catch { /* La sesión local ya se cerró. */ }
}
</script>

<template>
  <header class="topbar">
    <div class="top-inner">
      <a class="brand" href="/" aria-label="Wallnut">
        <span class="brand-symbol"><GraduationCap :size="22" aria-hidden="true" /></span>
        <span>Wallnut</span>
      </a>
      <div v-if="account" class="session-actions">
        <span class="role-chip">{{ roleNames[account.role] }}</span>
        <button type="button" class="button quiet" @click="signOut">Cerrar sesión</button>
      </div>
    </div>
  </header>
  <ConnectionStatus />
  <p v-if="storageNotice" class="session-storage-note state-note" role="status">{{ storageNotice }}</p>
  <Community v-if="account" :key="token" :account="account" :token="token" @expired="sessionExpired" />
  <main v-else-if="busy || saved" class="launch-screen">
    <section class="tile launch-panel">
      <img src="/ardy.webp" alt="" width="150" height="150" />
      <template v-if="busy || restoring">
        <h1>Abriendo Wallnut</h1>
        <p role="status"><span class="launch-spinner" aria-hidden="true"></span> Verificando tu sesión…</p>
      </template>
      <template v-else>
        <h1>Recuperar sesión</h1>
        <p class="error" role="alert">{{ message }}</p>
        <button class="button primary" @click="restore">Reintentar</button>
        <button class="button quiet" @click="signOut">Volver al inicio</button>
      </template>
    </section>
  </main>
  <SignIn v-else :message="message" :native="native" :remember="remember" @remember="remember = $event" @sign-in="signIn" />
</template>

<style scoped>
.session-storage-note { max-width: 1180px; margin: 14px auto; padding-inline: 20px; }
</style>
