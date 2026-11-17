<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { CalendarDays, MapPin, Plus } from '@lucide/vue'
import { api, errorText, RequestError, type Role } from './client'
import CampusProfileDialog from './CampusProfileDialog.vue'
import TournamentDialog from './TournamentDialog.vue'

const props = defineProps<{ token: string; role: Role }>()
const emit = defineEmits<{ expired: [] }>()
const categories = { workshop: 'Taller', tournament: 'Torneo', campus: 'Encuentro' }
type Category = keyof typeof categories
type TournamentFormat = 'individual' | 'doubles'
type EventCard = {
  id: string; title: string; description: string; category: Category; starts_at: string
  location: string; capacity: number; organizer: string; institutional: boolean; cancelled: boolean
  organizer_id: string; organizer_profile_visible: boolean
  mine: boolean; upcoming: boolean; attendees: number; enrolled: boolean; registration_open: boolean
  tournament_format: TournamentFormat
}
const defaults = {
  title: '', description: '', location: '', start: '', category: 'tournament' as Category, capacity: 16,
  tournament_format: 'individual' as TournamentFormat,
}
const form = reactive({ ...defaults })
const events = ref<EventCard[]>([])
const more = ref(false)
const creating = ref(false)
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const cancelling = ref('')
const openedProfile = ref('')
const openedTournament = ref('')
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
    const body = {
      ...fields, starts_at: `${start}:00-05:00`,
      tournament_format: fields.category === 'tournament' ? fields.tournament_format : 'individual',
    }
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

function tournamentGenerated() {
  events.value = events.value.map(item => item.id === openedTournament.value
    ? { ...item, registration_open: false }
    : item)
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
        <label>Cupos para estudiantes
          <input v-model.number="form.capacity" type="number" required max="500"
            :min="form.category === 'tournament' && form.tournament_format === 'doubles' ? 4 : 2"
            :step="form.category === 'tournament' && form.tournament_format === 'doubles' ? 2 : 1" />
        </label>
        <label v-if="form.category === 'tournament'">Modalidad
          <select v-model="form.tournament_format">
            <option value="individual">Individual</option>
            <option value="doubles">Por parejas</option>
          </select>
        </label>
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
            <span v-if="item.tournament_format === 'doubles'" class="badge">Por parejas</span>
            <span class="badge">{{ item.institutional ? 'Universidad' : 'Estudiantes' }}</span>
            <span v-if="item.cancelled" class="badge">Cancelado</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <span class="faculty-label"><MapPin :size="16" aria-hidden="true" /> {{ item.location }} · {{ format.format(new Date(item.starts_at)) }}</span>
          <p>
            <button v-if="item.organizer_profile_visible" type="button" class="organizer-profile-link"
              :aria-label="`Ver perfil de ${item.organizer}`" @click="openedProfile = item.organizer_id">{{ item.organizer }}</button>
            <template v-else>{{ item.organizer }}</template>
            · {{ item.attendees }} de {{ item.capacity }} cupos ocupados
          </p>
          <div class="workshop-actions">
            <button v-if="role === 'student' && item.registration_open" class="button secondary" type="button"
              :disabled="busy || (!item.enrolled && item.attendees >= item.capacity)" @click="update(item)">
              {{ item.enrolled ? 'Liberar mi cupo' : 'Inscribirme' }}
            </button>
            <button v-if="item.category === 'tournament'" class="button secondary" type="button"
              :aria-label="`Ver cuadro del torneo: ${item.title}`" @click="openedTournament = item.id">Ver cuadro</button>
            <template v-if="item.upcoming && !item.cancelled && (item.mine || role === 'admin')">
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
    <CampusProfileDialog v-if="openedProfile" :token="token" :student-id="openedProfile"
      @close="openedProfile = ''" @expired="emit('expired')" />
    <TournamentDialog v-if="openedTournament" :token="token" :event-id="openedTournament" :role="role"
      @close="openedTournament = ''" @generated="tournamentGenerated" @expired="emit('expired')" />
  </section>
</template>

<style scoped>
.organizer-profile-link { color: var(--blue); background: none; border: 0; padding: .25rem 0; font-weight: 700; text-decoration: underline; text-underline-offset: .15em; }
</style>
