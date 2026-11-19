<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api, errorText, RequestError } from './client'

type MovementKind = 'allocation' | 'evidence_reward' | 'coin_conversion'
interface Cursor { id: string; created_at: string; kind: MovementKind }
interface Movement extends Cursor {
  points: number
  actor: string | null
  course: string | null
  workshop: string | null
}
interface Ledger {
  faculty_id: string
  display_name: string
  generated_at: string
  allocated_points: number
  awarded_points: number
  converted_points: number
  available_points: number
  difference: number
  entries: Movement[]
  next_cursor: Cursor | null
}

const props = defineProps<{ token: string; facultyId: string }>()
const emit = defineEmits<{ expired: []; updated: [facultyId: string, available: number] }>()
const ledger = ref<Ledger>()
const entries = ref<Movement[]>([])
const loading = ref(false)
const problem = ref('')
const labels = { allocation: 'Asignación de Administración', evidence_reward: 'Recompensa por evidencia', coin_conversion: 'Canje de Coins a Points' }
const numbers = new Intl.NumberFormat('es-CO', { signDisplay: 'exceptZero' })
const total = new Intl.NumberFormat('es-CO')
const dates = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota' })
let revision = 0
let active = true

async function load(append = false) {
  if (append && (loading.value || !ledger.value?.next_cursor)) return
  const currentRevision = ++revision
  const query = new URLSearchParams()
  if (append && ledger.value?.next_cursor) {
    const cursor = ledger.value.next_cursor
    query.set('before', cursor.created_at)
    query.set('before_id', cursor.id)
    query.set('before_kind', cursor.kind)
  }
  loading.value = true
  problem.value = ''
  try {
    const value = await api<Ledger>(`/faculty-budgets/${props.facultyId}/ledger?${query}`, { token: props.token })
    if (!active || currentRevision !== revision) return
    ledger.value = value
    entries.value = append ? [...entries.value, ...value.entries] : value.entries
    emit('updated', value.faculty_id, value.available_points)
  } catch (error) {
    if (!active || currentRevision !== revision) return
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    if (active && currentRevision === revision) loading.value = false
  }
}

onMounted(() => load())
onBeforeUnmount(() => { active = false })
</script>

<template>
  <section class="budget-ledger" aria-labelledby="budget-ledger-title">
    <div class="section-heading">
      <div>
        <h3 id="budget-ledger-title">Movimientos del cupo</h3>
        <p v-if="ledger">{{ ledger.display_name }}</p>
      </div>
      <button class="button secondary" type="button" :disabled="loading" @click="load()">Actualizar movimientos</button>
    </div>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="loading" role="status">Consultando movimientos…</p>
    <template v-if="ledger">
      <dl class="budget-summary">
        <div><dt>Asignados</dt><dd>{{ total.format(ledger.allocated_points) }} Points</dd></div>
        <div><dt>Acreditados por evidencias</dt><dd>{{ total.format(ledger.awarded_points) }} Points</dd></div>
        <div><dt>Acreditados por canjes</dt><dd>{{ total.format(ledger.converted_points) }} Points</dd></div>
        <div><dt>Disponibles</dt><dd>{{ total.format(ledger.available_points) }} Points</dd></div>
      </dl>
      <p v-if="ledger.difference !== 0" class="error" role="alert">
        Hay una diferencia de {{ numbers.format(ledger.difference) }} Points entre el historial y el saldo disponible.
      </p>
      <p v-else class="success" role="status">Las asignaciones y acreditaciones coinciden con el saldo disponible.</p>
      <p class="ledger-cut">Consultado el <time :datetime="ledger.generated_at">{{ dates.format(new Date(ledger.generated_at)) }}</time></p>
      <p v-if="!entries.length" class="state-note">Todavía no hay movimientos en este cupo.</p>
      <ol v-else class="ledger-entries">
        <li v-for="entry in entries" :key="`${entry.kind}-${entry.id}`">
          <div>
            <strong>{{ labels[entry.kind] }}</strong>
            <p v-if="entry.actor">{{ entry.actor }}</p>
            <p v-if="entry.workshop">{{ entry.course }} · {{ entry.workshop }}</p>
            <time :datetime="entry.created_at">{{ dates.format(new Date(entry.created_at)) }}</time>
            <details class="ledger-reference"><summary>Referencia</summary><code>{{ entry.id }}</code></details>
          </div>
          <span class="ledger-points" :class="{ incoming: entry.points > 0 }">{{ numbers.format(entry.points) }} Points</span>
        </li>
      </ol>
    </template>
    <button v-if="ledger?.next_cursor || problem" class="button secondary" type="button" :disabled="loading"
      @click="load(!!ledger?.next_cursor)">{{ problem ? 'Reintentar consulta' : 'Ver movimientos anteriores' }}</button>
  </section>
</template>

<style scoped>
.budget-ledger { display: grid; gap: .8rem; border-top: 1px solid var(--line); margin-top: 1rem; padding-top: 1rem; }
.budget-ledger .section-heading { gap: .7rem; }
.budget-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr)); gap: .5rem; margin: 0; }
.budget-summary div { padding: .65rem; background: var(--light); border-radius: 10px; }
.budget-summary dt { color: var(--muted); font-size: .85rem; }
.budget-summary dd { margin: .25rem 0 0; font-weight: 750; }
.ledger-cut, .ledger-entries time { font-size: .8rem; color: var(--muted); }
.ledger-entries { list-style: none; padding: 0; margin: 0; }
.ledger-entries li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: .5rem 1rem; padding: .85rem 0; border-top: 1px solid var(--line); }
.ledger-entries li > div { min-width: 0; }
.ledger-entries li p { font-size: .88rem; margin: .15rem 0; }
.ledger-points { font-weight: 750; white-space: nowrap; }
.ledger-points.incoming { color: #1a6647; }
.ledger-reference { margin-top: .35rem; font-size: .8rem; color: var(--muted); }
.ledger-reference summary { cursor: pointer; }
.ledger-reference code { display: block; overflow-wrap: anywhere; padding: .3rem 0; }
</style>
