<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Capacitor } from '@capacitor/core'
import { GraduationCap } from '@lucide/vue'
import type { Account } from './client'
import { api, errorText, RequestError } from './client'
import SignIn from './SignIn.vue'
import Community from './Community.vue'
import ConnectionStatus from './ConnectionStatus.vue'

const token = ref('')
const account = ref<Account | null>(null)
const busy = ref(false)
const message = ref('')
const native = Capacitor.isNativePlatform()
const sessionKey = 'wallnut.session'
const saved = ref('')
try { saved.value = sessionStorage.getItem(sessionKey) ?? '' } catch { /* La sesión puede mantenerse en memoria. */ }
const restoring = ref(Boolean(saved.value))
const roleNames = { student: 'Estudiante', faculty: 'Docente', admin: 'Administración', staff: 'Personal' }
let sessionRevision = 0

function setSession(value: string, user: Account) {
  token.value = value
  account.value = user
  saved.value = value
  try { sessionStorage.setItem(sessionKey, value) } catch { /* La sesión puede mantenerse en memoria. */ }
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
onMounted(restore)

async function signIn(credential: string) {
  if (busy.value) return
  const revision = ++sessionRevision
  busy.value = true
  message.value = ''
  try {
    const session = await api<{ token: string; account: Account }>('/session', {
      method: 'POST', data: { credential },
    })
    if (revision === sessionRevision) setSession(session.token, session.account)
  } catch (error) {
    if (revision === sessionRevision) message.value = errorText(error)
  } finally {
    if (revision === sessionRevision) busy.value = false
  }
}

function clearSession(notice = '') {
  sessionRevision++
  busy.value = false
  restoring.value = false
  token.value = ''
  account.value = null
  saved.value = ''
  try { sessionStorage.removeItem(sessionKey) } catch { /* La sesión en memoria ya se cerró. */ }
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
  <SignIn v-else :message="message" :native="native" @sign-in="signIn" />
</template>
