<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, errorText, RequestError, type FacultyBudget } from './client'

const props = defineProps<{ token: string; accountId: string; allocate?: boolean }>()
const emit = defineEmits<{ expired: [] }>()
const budgets = ref<FacultyBudget[]>([])
const teacher = ref('')
const points = ref<number | ''>('')
const loading = ref(false)
const saving = ref(false)
const problem = ref('')
const notice = ref('')
const numbers = new Intl.NumberFormat('es-CO')

interface Allocation {
  faculty_id: string
  points: number
  request_id: string
}

const storageKey = `wallnut.pending-allocation.${props.accountId}`
function readPending(): Allocation | null {
  if (!props.allocate) return null
  try {
    const saved = sessionStorage.getItem(storageKey)
    if (!saved) return null
    const item: Allocation = JSON.parse(saved)
    return typeof item?.faculty_id === 'string' && typeof item.request_id === 'string'
      && Number.isSafeInteger(item.points) && item.points > 0 ? item : null
  } catch {
    return null
  }
}

const pending = ref(readPending())
if (pending.value) {
  teacher.value = pending.value.faculty_id
  points.value = pending.value.points
}

function remember(value: Allocation | null) {
  pending.value = value
  try {
    if (value) sessionStorage.setItem(storageKey, JSON.stringify(value))
    else sessionStorage.removeItem(storageKey)
  } catch {
    // El reintento sigue disponible durante esta vista.
  }
}

function handleError(error: unknown) {
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else problem.value = errorText(error)
}

async function load() {
  loading.value = true
  problem.value = ''
  try {
    budgets.value = await api<FacultyBudget[]>('/faculty-budgets', { token: props.token })
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function assign() {
  if (!props.allocate || saving.value) return
  const amount = Number(points.value)
  if (!pending.value && (!teacher.value || !Number.isSafeInteger(amount) || amount <= 0)) return
  const allocation = pending.value ?? { faculty_id: teacher.value, points: amount, request_id: crypto.randomUUID() }
  remember(allocation)
  saving.value = true
  problem.value = ''
  notice.value = ''
  try {
    await api(`/faculty-budgets/${allocation.faculty_id}/allocations`, {
      token: props.token, method: 'POST',
      data: { points: allocation.points, request_id: allocation.request_id },
    })
    remember(null)
    points.value = ''
    notice.value = `Se asignaron ${numbers.format(allocation.points)} Ardi Points al cupo docente.`
    await load()
  } catch (error) {
    if (error instanceof RequestError && [400, 403, 404, 409, 422].includes(error.status)) remember(null)
    handleError(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="tile faculty-budget" aria-labelledby="faculty-budget-title">
    <div class="faculty-budget-heading">
      <img src="/ardi-points.png" alt="" width="44" height="44" loading="lazy" />
      <h2 id="faculty-budget-title">{{ allocate ? 'Cupos docentes' : 'Mi cupo docente' }}</h2>
    </div>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="loading" class="state-note" role="status">Consultando cupos…</p>
    <p v-else-if="!budgets.length && !problem" class="state-note">No hay cupos docentes disponibles.</p>
    <ul v-if="budgets.length" class="budget-balances">
      <li v-for="budget in budgets" :key="budget.faculty_id">
        <span>{{ allocate ? budget.display_name : 'Disponibles para acreditar' }}</span>
        <strong>{{ numbers.format(budget.available_points) }} Points</strong>
      </li>
    </ul>
    <button v-if="problem && !budgets.length && !pending" class="button quiet" type="button" @click="load">Volver a consultar</button>
    <form v-if="allocate && (budgets.length || pending)" class="form-stack budget-form" @submit.prevent="assign">
      <p v-if="pending && !saving" class="state-note">Hay una asignación por confirmar. Reintenta con los mismos datos.</p>
      <label>Docente
        <select v-model="teacher" required :disabled="saving || !!pending">
          <option value="" disabled>Selecciona un docente</option>
          <option v-for="budget in budgets" :key="budget.faculty_id" :value="budget.faculty_id">{{ budget.display_name }}</option>
        </select>
      </label>
      <label>Points por asignar
        <input v-model.number="points" type="number" min="1" step="1" required :disabled="saving || !!pending" />
      </label>
      <button class="button primary" type="submit" :disabled="saving || loading">
        {{ saving ? 'Asignando…' : pending ? 'Confirmar asignación pendiente' : 'Asignar Points' }}
      </button>
    </form>
  </section>
</template>
