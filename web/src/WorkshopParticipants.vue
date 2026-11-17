<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, errorText, RequestError, type Workshop } from './client'

interface Participant {
  student_id: string
  display_name: string
  checked_in_at: string | null
  evidence_status: 'submitted' | 'returned' | 'approved' | null
}

const props = defineProps<{ token: string; workshop: Workshop }>()
const emit = defineEmits<{ expired: [] }>()
const rows = ref<Participant[]>()
const busy = ref(false)
const problem = ref('')
const query = ref('')
const attendance = ref<'all' | 'present' | 'pending'>('all')
const labels = { submitted: 'entregada', returned: 'devuelta', approved: 'aprobada' }
const dateTime = new Intl.DateTimeFormat('es-CO', {
  day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', timeZone: 'America/Bogota',
})

function normalized(text: string) {
  return text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('es-CO')
}

const presentCount = computed(() => rows.value?.filter(row => row.checked_in_at).length ?? 0)
const matching = computed(() => (rows.value ?? []).filter(row => {
  if (attendance.value === 'present' && !row.checked_in_at) return false
  if (attendance.value === 'pending' && row.checked_in_at) return false
  return normalized(row.display_name).includes(normalized(query.value.trim()))
}))

async function load() {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  try {
    rows.value = await api<Participant[]>(`/workshops/${props.workshop.id}/participants`, { token: props.token })
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="workshop-participants" aria-label="Inscripciones y asistencia">
    <div class="participants-summary">
      <p v-if="rows" role="status">{{ rows.length }} de {{ workshop.capacity }} cupos · {{ presentCount }} asistencias</p>
      <button class="button secondary" type="button" :disabled="busy" @click="load">Actualizar lista</button>
    </div>
    <p v-if="workshop.cancelled_at" class="state-note">El taller fue cancelado. Estas son las inscripciones que quedaron registradas.</p>
    <p v-if="busy" role="status">Cargando la lista…</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="rows?.length === 0">Todavía no hay inscripciones.</p>
    <template v-if="rows?.length">
      <div class="form-stack participant-filters">
        <label>Nombre <input v-model="query" type="search" placeholder="Busca un estudiante" /></label>
        <label>Asistencia
          <select v-model="attendance">
            <option value="all">Todas</option>
            <option value="present">Registrada</option>
            <option value="pending">Sin registrar</option>
          </select>
        </label>
      </div>
      <p v-if="matching.length === 0" role="status">Ninguna inscripción coincide con los filtros.</p>
      <ul v-else class="participant-list">
        <li v-for="row in matching" :key="row.student_id" class="tile participant-row">
          <div>
            <strong>{{ row.display_name }}</strong>
            <p v-if="row.checked_in_at">Asistencia · {{ dateTime.format(new Date(row.checked_in_at)) }}</p>
            <p v-else>Asistencia sin registrar</p>
          </div>
          <span :class="{ approved: row.evidence_status === 'approved' }">
            {{ row.evidence_status ? `Evidencia ${labels[row.evidence_status]}` : 'Sin evidencia' }}
          </span>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.workshop-participants { display: grid; gap: .75rem; }
.participants-summary { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .45rem; }
.participant-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); }
.participant-list { display: grid; gap: .5rem; list-style: none; margin: 0; padding: 0; }
.participant-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .4rem; padding: .7rem; }
.participant-row p { font-size: .88rem; margin: .2rem 0 0; }
.participant-row span { border-radius: 1rem; padding: .2rem .65rem; background: var(--light); color: var(--ink); font-size: .8rem; }
.participant-row span.approved { background: #e3f5e9; color: #184b2e; }
</style>
