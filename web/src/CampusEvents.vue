<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { CalendarDays, MapPin, Plus } from '@lucide/vue'
import { api, errorText, RequestError, type Role } from './client'

const props = defineProps<{ token: string; role: Role }>()
const emit = defineEmits<{ expired: [] }>()
const categories = { workshop: 'Taller', tournament: 'Torneo', campus: 'Encuentro' }
type Category = keyof typeof categories
type EventCard = {
  id: string; title: string; description: string; category: Category; starts_at: string
  location: string; capacity: number; organizer: string; institutional: boolean; cancelled: boolean
  mine: boolean; upcoming: boolean; attendees: number; enrolled: boolean
}
const defaults = { title: '', description: '', location: '', start: '', category: 'tournament' as Category, capacity: 16 }
const form = reactive({ ...defaults })
const events = ref<EventCard[]>([])
const more = ref(false)
const creating = ref(false)
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const cancelling = ref('')
const format = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota' })
let pending: { id: string; fingerprint: string } | undefined

async function perform(action: () => Promise<void>) {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    await action()
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

async function fetchEvents(append = false) {
  const rows = await api<EventCard[]>(`/campus-events?offset=${append ? events.value.length : 0}`, { token: props.token })
  more.value = rows.length > 20
  events.value = [...(append ? events.value : []), ...rows.slice(0, 20)]
}

function publish() {
  void perform(async () => {
    const { start, ...fields } = form
    const body = { ...fields, starts_at: `${start}:00-05:00` }
    const fingerprint = JSON.stringify(body)
    if (pending?.fingerprint !== fingerprint) pending = { fingerprint, id: crypto.randomUUID() }
    await api('/campus-events', { token: props.token, method: 'POST', data: { ...body, id: pending.id } })
    pending = undefined
    Object.assign(form, defaults)
    creating.value = false
    await fetchEvents()
    notice.value = 'Evento publicado en Comunidad.'
  })
}

function update(item: EventCard, cancel = false) {
  void perform(async () => {
    const action = cancel ? 'cancel' : 'enrollment'
    const updated = await api<EventCard>(`/campus-events/${item.id}/${action}`, {
      token: props.token, method: !cancel && item.enrolled ? 'DELETE' : 'PUT',
    })
    events.value = events.value.map(row => row.id === updated.id ? updated : row)
    cancelling.value = ''
    notice.value = cancel ? 'Evento cancelado.' : updated.enrolled ? 'Cupo reservado.' : 'Cupo liberado.'
  })
}

onMounted(() => perform(fetchEvents))
</script>

<template>
  <section class="campus-events" aria-labelledby="campus-events-heading">
    <div class="section-heading">
      <div><h2 id="campus-events-heading">Eventos del campus</h2><p>Talleres, encuentros y torneos de la comunidad.</p></div>
      <button v-if="role !== 'staff'" class="button primary" type="button" :disabled="busy" @click="creating = !creating">
        <Plus :size="18" aria-hidden="true" /> {{ creating ? 'Cerrar formulario' : 'Crear evento' }}
      </button>
    </div>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <form v-if="creating" class="tile form-stack campus-event-form" @submit.prevent="publish">
      <label>Nombre del evento <input v-model="form.title" required minlength="3" maxlength="100" placeholder="Torneo de pádel" /></label>
      <div class="ardy-options">
        <label>Tipo
          <select v-model="form.category">
            <option v-for="(label, value) in categories" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <label>Cupos <input v-model.number="form.capacity" type="number" required min="2" max="500" /></label>
        <label>Inicio en Ibagué <input v-model="form.start" type="datetime-local" required /></label>
        <label>Lugar <input v-model="form.location" required minlength="2" maxlength="100" /></label>
      </div>
      <label>Descripción <textarea v-model="form.description" required minlength="5" maxlength="1200" rows="3"></textarea></label>
      <button class="button primary" :disabled="busy">Publicar evento</button>
    </form>
    <p v-if="busy && !events.length" class="state-note" role="status">Cargando eventos…</p>
    <p v-else-if="!events.length && !problem" class="tile state-note">Todavía no hay eventos próximos.</p>
    <div v-else class="feed-list">
      <article v-for="item in events" :key="item.id" class="tile call-card">
        <div class="call-icon"><CalendarDays :size="24" aria-hidden="true" /></div>
        <div class="call-content">
          <div class="call-meta">
            <span>{{ categories[item.category] }}</span>
            <span class="badge">{{ item.institutional ? 'Universidad' : 'Estudiantes' }}</span>
            <span v-if="item.cancelled" class="badge">Cancelado</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <span class="faculty-label"><MapPin :size="16" aria-hidden="true" /> {{ item.location }} · {{ format.format(new Date(item.starts_at)) }}</span>
          <p>{{ item.organizer }} · {{ item.attendees }} de {{ item.capacity }} cupos ocupados</p>
          <div v-if="item.upcoming && !item.cancelled" class="workshop-actions">
            <button v-if="role === 'student'" class="button secondary" type="button"
              :disabled="busy || (!item.enrolled && item.attendees >= item.capacity)" @click="update(item)">
              {{ item.enrolled ? 'Liberar mi cupo' : 'Inscribirme' }}
            </button>
            <template v-if="item.mine || role === 'admin'">
              <button v-if="cancelling === item.id" class="button secondary" type="button" :disabled="busy"
                @click="update(item, true)">Confirmar cancelación</button>
              <button v-else class="button quiet" type="button" :disabled="busy" @click="cancelling = item.id">Cancelar evento</button>
            </template>
          </div>
        </div>
      </article>
    </div>
    <button v-if="more || problem" class="button secondary show-more" :disabled="busy"
      @click="perform(() => fetchEvents(!problem))">{{ problem ? 'Actualizar eventos' : 'Ver más eventos' }}</button>
  </section>
</template>
