<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Wifi, WifiOff } from '@lucide/vue'
import { api, RequestError } from './client'
import { connection } from './connectivity'

const state = ref(connection.state)
const checking = ref(false)
const problem = ref('')
const unsubscribe = connection.subscribe(value => { state.value = value })
const visible = computed(() => state.value.reachable === false || state.value.recovered || !!problem.value)
const healthy = computed(() => state.value.reachable === true && !problem.value)
const heading = computed(() => problem.value ? 'Wallnut aún no está disponible'
  : healthy.value ? 'La conexión volvió'
    : !state.value.online ? 'Tu dispositivo indica que estás sin conexión' : 'No pudimos confirmar la conexión con Wallnut')
let active = true
let revision = 0

async function check() {
  if (checking.value) return
  const current = ++revision
  checking.value = true
  problem.value = ''
  try {
    const result = await api<{ status: string }>('/ready')
    if (active && current === revision && result.status !== 'ready') problem.value = 'El servicio todavía no está listo. Prueba de nuevo más tarde.'
  } catch (error) {
    if (active && current === revision && error instanceof RequestError) problem.value = 'El servicio todavía no está listo. Prueba de nuevo más tarde.'
  } finally {
    if (active && current === revision) checking.value = false
  }
}

function online() {
  connection.setOnline(true)
  void check()
}

function offline() {
  revision++
  checking.value = false
  problem.value = ''
  connection.setOnline(false)
}

function dismiss() {
  problem.value = ''
  connection.dismissRecovery()
}

onMounted(() => {
  connection.setOnline(navigator.onLine)
  window.addEventListener('online', online)
  window.addEventListener('offline', offline)
})
onBeforeUnmount(() => {
  active = false
  unsubscribe()
  window.removeEventListener('online', online)
  window.removeEventListener('offline', offline)
})
</script>

<template>
  <aside v-if="visible" class="connection-status" :class="{ recovered: healthy }" role="status" aria-live="polite" aria-atomic="true">
    <component :is="healthy ? Wifi : WifiOff" :size="24" aria-hidden="true" />
    <div><strong>{{ heading }}</strong>
      <p v-if="problem">{{ problem }}</p>
      <p v-else-if="healthy">Actualiza la sección que estabas consultando. Si se interrumpió un pago o un envío, comprueba su resultado antes de repetirlo.</p>
      <p v-else>Conserva esta pantalla para mantener lo que estás escribiendo. Cuando vuelva la conexión, comprueba el resultado de un pago o un envío antes de repetirlo.</p>
    </div>
    <button v-if="healthy" class="button quiet" type="button" @click="dismiss">Cerrar aviso</button>
    <button v-else class="button secondary" type="button" :disabled="checking" @click="check">{{ checking ? 'Comprobando…' : 'Comprobar conexión' }}</button>
  </aside>
</template>

<style scoped>
.connection-status { display: flex; align-items: start; flex-wrap: wrap; gap: 10px 14px; max-width: 1180px; margin: 16px auto; padding: 15px 20px; background: #fff3dc; color: #69470d; border: 1px solid #e7ca8d; border-radius: 14px; }
.connection-status > div { flex: 1; min-width: min(100%, 210px); }
.connection-status p { margin: 5px 0 0; font-size: .9rem; line-height: 1.5; }
.connection-status.recovered { background: #edf8f1; color: #245f40; border-color: #b8ddc6; }
@media (max-width: 1210px) { .connection-status { margin-inline: 16px; } }
</style>
