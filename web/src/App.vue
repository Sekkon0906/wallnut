<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Capacitor } from '@capacitor/core'
import { GraduationCap } from '@lucide/vue'
import type { Account } from './client'
import { api, errorText, RequestError } from './client'
import SignIn from './SignIn.vue'
import Community from './Community.vue'

const token = ref('')
const account = ref<Account | null>(null)
const busy = ref(false)
const message = ref('')
const native = Capacitor.isNativePlatform()
const sessionKey = 'wallnut.session'
const saved = ref(sessionStorage.getItem(sessionKey) ?? '')
const restoring = ref(Boolean(saved.value))
const roleNames = { student: 'Estudiante', faculty: 'Docente', admin: 'Administración', staff: 'Personal' }

function setSession(value: string, user: Account) {
  token.value = value
  account.value = user
  saved.value = value
  sessionStorage.setItem(sessionKey, value)
}

async function restore() {
  if (!saved.value) return
  restoring.value = true
  message.value = ''
  try {
    const user = await api<Account>('/session', { token: saved.value })
    setSession(saved.value, user)
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) clearSession('La sesión terminó. Vuelve a ingresar.')
    else message.value = errorText(error)
  } finally {
    restoring.value = false
  }
}
onMounted(restore)

async function signIn(credential: string) {
  if (busy.value) return
  busy.value = true
  message.value = ''
  try {
    const session = await api<{ token: string; account: Account }>('/session', {
      method: 'POST', data: { credential },
    })
    setSession(session.token, session.account)
  } catch (error) {
    message.value = errorText(error)
  } finally {
    busy.value = false
  }
}

function clearSession(notice = '') {
  token.value = ''
  account.value = null
  saved.value = ''
  sessionStorage.removeItem(sessionKey)
  message.value = notice
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
  <Community v-if="account" :account="account" :token="token"
    @expired="clearSession('La sesión terminó. Vuelve a ingresar.')" />
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
