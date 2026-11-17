<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ArrowRight, BookOpen, ShieldCheck } from '@lucide/vue'
import { googleClientId, localDemo } from './client'
import { renderGoogleSignIn } from './google'

const props = defineProps<{ message: string; native: boolean }>()
const emit = defineEmits<{ signIn: [credential: string] }>()
const button = ref<HTMLElement>()
const googleError = ref('')
const nativeBusy = ref(false)
let nativeSetup: Promise<void> | undefined

async function nativeSignIn() {
  if (nativeBusy.value) return
  nativeBusy.value = true
  googleError.value = ''
  try {
    const { SocialLogin } = await import('@capgo/capacitor-social-login')
    nativeSetup ??= SocialLogin.initialize({ google: { webClientId: googleClientId, mode: 'online' } })
    await nativeSetup
    const { result } = await SocialLogin.login({ provider: 'google', options: {} })
    if (!('idToken' in result) || !result.idToken) throw new Error('Missing Google ID token')
    emit('signIn', result.idToken)
  } catch {
    nativeSetup = undefined
    googleError.value = 'No pudimos completar el acceso de Google. Vuelve a intentarlo.'
  } finally {
    nativeBusy.value = false
  }
}

onMounted(async () => {
  if (!googleClientId || !button.value || props.native) return
  try {
    await renderGoogleSignIn(button.value, googleClientId, (credential) => emit('signIn', credential))
  } catch (error) {
    googleError.value = error instanceof Error ? error.message : 'El acceso institucional no está disponible.'
  }
})
</script>

<template>
  <main class="sign-in">
    <section class="sign-hero">
      <div class="sign-copy">
        <p class="campus-name"><BookOpen :size="17" aria-hidden="true" /> Comunidad Unibagué</p>
        <h1>Tu campus,<br />en Wallnut.</h1>
        <p>Encuentra talleres, participa en el campus y lleva tu Ardy contigo.</p>
      </div>
      <img src="/ardy.webp" alt="Ardy, la ardilla de Wallnut" />
    </section>
    <section class="sign-panel">
      <ShieldCheck :size="30" class="accent-icon" aria-hidden="true" />
      <h2>Entra a Wallnut</h2>
      <p>Usa tu cuenta institucional de Google.</p>
      <div v-if="!native && googleClientId" ref="button" class="google-area"></div>
      <button v-else-if="native && googleClientId" class="button secondary"
        :disabled="nativeBusy" @click="nativeSignIn">{{ nativeBusy ? 'Abriendo Google…' : 'Continuar con Google' }}</button>
      <p v-else-if="!localDemo" class="state-note">
        El acceso institucional aún no está configurado en esta versión.
      </p>
      <p v-if="googleError || message" role="alert" class="error">{{ googleError || message }}</p>
      <div v-if="localDemo" class="demo-login">
        <h3>Demostración local</h3>
        <button class="button primary" @click="emit('signIn', 'demo-student')">
          Entrar como estudiante <ArrowRight :size="17" aria-hidden="true" />
        </button>
        <button class="button quiet" @click="emit('signIn', 'demo-second-student')">
          Entrar como Mateo · estudiante de prueba
        </button>
        <details>
          <summary>Más cuentas para torneos</summary>
          <button class="button quiet" type="button" @click="emit('signIn', 'demo-third-student')">Entrar como Camila</button>
          <button class="button quiet" type="button" @click="emit('signIn', 'demo-fourth-student')">Entrar como Julián</button>
        </details>
        <button class="button secondary" @click="emit('signIn', 'demo-faculty')">
          Entrar como docente
        </button>
        <button class="button quiet" @click="emit('signIn', 'demo-admin')">
          Entrar como administración
        </button>
      </div>
    </section>
  </main>
</template>
