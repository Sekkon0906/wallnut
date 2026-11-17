<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ArrowUpRight, BookOpen, CalendarDays, ChevronRight, GraduationCap, Megaphone, Plus, Trophy, UserRound, Wallet as WalletIcon, X } from '@lucide/vue'
import Administration from './Administration.vue'
import FacultyBudgetView from './FacultyBudgetView.vue'
import GradeRedemptionView from './GradeRedemptionView.vue'
import WorkshopAgenda from './WorkshopAgenda.vue'
import WalletView from './WalletView.vue'
import MyArdyView from './MyArdyView.vue'
import ParticipationRanking from './ParticipationRanking.vue'
import CampusEvents from './CampusEvents.vue'
import { api, errorText, localDemo, RequestError, type Account, type Application, type Course, type WorkshopCall } from './client'

const props = defineProps<{ account: Account; token: string }>()
const emit = defineEmits<{ expired: [] }>()
type Filter = 'all' | 'open' | 'mine'
type Dialog = 'create' | 'apply' | 'review' | 'schedule'
const filters: { id: Filter; label: string }[] = [
  { id: 'all', label: 'Todas' },
  { id: 'open', label: 'Abiertas' },
  { id: 'mine', label: 'Mis postulaciones' },
]
const calls = ref<WorkshopCall[]>([])
const courses = ref<Course[]>([])
const applications = ref<Application[]>([])
const filter = ref<Filter>('all')
const view = ref<'community' | 'groups' | 'agenda' | 'wallet' | 'grade' | 'ardy' | 'ranking'>(
  props.account.role === 'admin' ? 'groups' : 'community',
)
const gradeCourse = ref<Course>()
const modal = ref<HTMLDialogElement>()
const dialog = ref<Dialog | null>(null)
const selected = ref<WorkshopCall>()
const loading = ref(false)
const busy = ref(false)
const problem = ref('')
const modalError = ref('')
const notice = ref('')
const publish = reactive({ course_id: '', title: '', description: '' })
const submission = reactive({ proposal: '', evidence_url: '' })
const enrollment = reactive({ course_id: '', email: '' })
const schedule = reactive({ starts_at: '', ends_at: '', location: '', capacity: 25 })
const hasMore = ref(false)
const pageSize = 25
let offset = 0

const filteredCalls = computed(() => calls.value.filter((item) => {
  if (filter.value === 'open') return item.open
  if (filter.value === 'mine') return item.my_application !== null
  return true
}))

const statusLabels = {
  pending: 'En revisión',
  approved: 'Seleccionado',
  not_selected: 'Convocatoria cerrada',
}

const isFaculty = computed(() => props.account.role === 'faculty')
const isStudent = computed(() => props.account.role === 'student')
const isAdmin = computed(() => props.account.role === 'admin')
const firstName = computed(() => props.account.display_name.split(' ')[0])
const roleHome = {
  student: { title: 'Comunidad', description: 'Inscríbete a un taller, comparte lo que sabes o personaliza tu Ardy.' },
  faculty: { title: 'Espacio docente', description: 'Publica convocatorias, revisa evidencias y gestiona tus grupos.' },
  admin: { title: 'Comunidad', description: 'Consulta las convocatorias y la agenda de la comunidad.' },
  staff: { title: 'Comunidad', description: 'Consulta la agenda. Administración puede habilitar tus funciones docentes.' },
}

function openGradeRedemption(course: Course) {
  gradeCourse.value = course
  view.value = 'grade'
}

function handleError(error: unknown, target: typeof problem) {
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else target.value = errorText(error)
}

async function loadCalls(append = false) {
  if (loading.value) return
  loading.value = true
  problem.value = ''
  try {
    const currentOffset = append ? offset : 0
    const batch = await api<WorkshopCall[]>(
      `/workshop-calls?offset=${currentOffset}&limit=${pageSize}`, { token: props.token },
    )
    calls.value = append ? [...calls.value, ...batch] : batch
    offset = currentOffset + batch.length
    hasMore.value = batch.length === pageSize
  } catch (error) {
    handleError(error, problem)
  } finally {
    loading.value = false
  }
}

async function loadCourses() {
  try {
    courses.value = await api<Course[]>('/courses', { token: props.token })
  } catch (error) {
    handleError(error, problem)
  }
}

onMounted(() => Promise.all([loadCalls(), loadCourses()]))

async function openDialog(mode: Dialog, call?: WorkshopCall) {
  selected.value = call
  modalError.value = ''
  dialog.value = mode
  if (mode === 'create') Object.assign(publish, { course_id: '', title: '', description: '' })
  if (mode === 'apply') Object.assign(submission, { proposal: '', evidence_url: '' })
  if (mode === 'review') applications.value = []
  if (mode === 'schedule') {
    Object.assign(schedule, { starts_at: '', ends_at: '', location: '', capacity: 25 })
  }
  await nextTick()
  modal.value?.showModal()
  if (mode === 'review' && call) {
    try {
      applications.value = await api<Application[]>(`/workshop-calls/${call.id}/applications`, {
        token: props.token,
      })
    } catch (error) {
      handleError(error, modalError)
    }
  }
}

function closeDialog() {
  if (!busy.value) modal.value?.close()
}

function submitCall() {
  return mutate(async () => {
    await api('/workshop-calls', { token: props.token, method: 'POST', data: publish })
    return 'Convocatoria publicada.'
  })
}

function submitApplication() {
  if (!selected.value) return
  const callId = selected.value.id
  return mutate(async () => {
    await api(`/workshop-calls/${callId}/applications`, {
      token: props.token,
      method: 'POST',
      data: { proposal: submission.proposal, evidence_url: submission.evidence_url || null },
    })
    return 'Tu postulación quedó en revisión.'
  })
}

function approveApplication(application: Application) {
  if (!selected.value) return
  const callId = selected.value.id
  return mutate(async () => {
    await api(`/workshop-calls/${callId}/applications/${application.id}/approval`, {
      token: props.token,
      method: 'PUT',
    })
    return `${application.display_name} quedó como tallerista de esta convocatoria.`
  })
}

async function scheduleWorkshop() {
  if (!selected.value) return
  const callId = selected.value.id
  const start = new Date(`${schedule.starts_at}-05:00`)
  const end = new Date(`${schedule.ends_at}-05:00`)
  if (!Number.isFinite(start.valueOf()) || !Number.isFinite(end.valueOf()) || end <= start) {
    modalError.value = 'La fecha de fin debe ser posterior a la de inicio.'
    return
  }
  await mutate(async () => {
    await api(`/workshop-calls/${callId}/workshop`, {
      token: props.token,
      method: 'POST',
      data: { ...schedule, starts_at: start.toISOString(), ends_at: end.toISOString() },
    })
    view.value = 'agenda'
    return 'Taller agendado. Ya aparece en la agenda.'
  })
}

async function mutate(work: () => Promise<string>) {
  if (busy.value) return
  busy.value = true
  modalError.value = ''
  notice.value = ''
  try {
    notice.value = await work()
    modal.value?.close()
    await loadCalls()
  } catch (error) {
    handleError(error, modalError)
  } finally {
    busy.value = false
  }
}

async function confirmEnrollment() {
  if (busy.value) return
  busy.value = true
  notice.value = ''
  problem.value = ''
  try {
    await api(`/courses/${enrollment.course_id}/students`, {
      token: props.token, method: 'PUT', data: { email: enrollment.email },
    })
    enrollment.email = ''
    notice.value = 'Matrícula confirmada.'
  } catch (error) {
    handleError(error, problem)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="dashboard">
    <div v-if="localDemo" class="demo-banner">Demostración local · cuentas y datos ficticios</div>
    <nav class="views" :class="{ 'views-with-wallet': isStudent }" aria-label="Secciones">
      <button class="view-link" :aria-current="view === 'community' ? 'page' : undefined" @click="view = 'community'">
        <Megaphone :size="19" aria-hidden="true" /> Comunidad
      </button>
      <button class="view-link" :aria-current="view === 'agenda' ? 'page' : undefined" @click="view = 'agenda'">
        <CalendarDays :size="19" aria-hidden="true" /> Agenda
      </button>
      <button class="view-link" :aria-current="view === 'groups' || view === 'grade' ? 'page' : undefined" @click="view = 'groups'">
        <BookOpen :size="19" aria-hidden="true" /> {{ isAdmin ? 'Administración' : 'Mis grupos' }}
      </button>
      <button v-if="isStudent" class="view-link" :aria-current="view === 'wallet' ? 'page' : undefined"
        @click="view = 'wallet'">
        <WalletIcon :size="19" aria-hidden="true" /> Billetera
      </button>
      <button class="view-link" :aria-current="view === 'ranking' ? 'page' : undefined" @click="view = 'ranking'">
        <Trophy :size="19" aria-hidden="true" /> Ranking
      </button>
      <button v-if="isStudent" class="view-link" :aria-current="view === 'ardy' ? 'page' : undefined" @click="view = 'ardy'">
        <UserRound :size="19" aria-hidden="true" /> Mi Ardy
      </button>
    </nav>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>

    <template v-if="view === 'community'">
      <section class="community-hero">
        <div>
          <p class="hero-kicker">Hola, {{ firstName }}</p>
          <h1>{{ roleHome[account.role].title }}</h1>
          <p>{{ roleHome[account.role].description }}</p>
          <div class="workshop-actions role-shortcuts">
            <button class="button secondary" type="button" @click="view = 'agenda'">Ver agenda</button>
            <button v-if="isStudent" class="button secondary" type="button" @click="view = 'ardy'">Personalizar mi Ardy</button>
            <button v-if="isFaculty" class="button secondary" type="button" @click="view = 'groups'">Gestionar grupos</button>
          </div>
        </div>
        <img src="/ardy.webp" alt="" />
      </section>

      <CampusEvents :token="token" :role="account.role" @expired="emit('expired')" />

      <div class="section-heading">
        <div>
          <h2>Convocatorias</h2>
          <p v-if="isStudent">Postúlate para orientar un taller en el campus.</p>
        </div>
        <button v-if="isFaculty && courses.length" class="button primary" @click="openDialog('create')">
          <Plus :size="18" aria-hidden="true" /> Publicar convocatoria
        </button>
      </div>

      <div class="filters" aria-label="Filtrar convocatorias">
        <button v-for="item in filters.filter((item) => item.id !== 'mine' || isStudent)"
          :key="item.id" class="filter" :aria-pressed="filter === item.id"
          @click="filter = item.id">{{ item.label }}</button>
      </div>
      <p v-if="loading && !calls.length" class="state-note" role="status">Cargando convocatorias…</p>
      <p v-else-if="!filteredCalls.length && !problem" class="tile state-note">No hay convocatorias en esta vista.</p>
      <div class="feed-list">
        <article v-for="item in filteredCalls" :key="item.id" class="tile call-card">
          <div class="call-icon"><Megaphone :size="25" aria-hidden="true" /></div>
          <div class="call-content">
            <div class="call-meta">
              <span>{{ item.course }}</span>
              <span v-if="item.my_application" class="badge">{{ statusLabels[item.my_application] }}</span>
              <span v-else-if="!item.open" class="badge">Tallerista confirmado</span>
            </div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.description }}</p>
            <span class="faculty-label"><GraduationCap :size="17" aria-hidden="true" /> {{ item.faculty }}</span>
            <button v-if="item.open && isStudent && !item.my_application" class="button quiet action"
              @click="openDialog('apply', item)">Postularme <ArrowUpRight :size="17" aria-hidden="true" /></button>
            <button v-if="item.can_manage" class="button quiet action"
              @click="openDialog('review', item)">Revisar postulaciones <ChevronRight :size="17" aria-hidden="true" /></button>
            <button v-if="item.can_schedule" class="button secondary action schedule-action"
              @click="openDialog('schedule', item)">Agendar taller <CalendarDays :size="17" aria-hidden="true" /></button>
          </div>
        </article>
      </div>
      <button v-if="hasMore" class="button secondary show-more" :disabled="loading" @click="loadCalls(true)">Cargar más</button>
      <button v-if="problem && !calls.length" class="button secondary" @click="loadCalls()">Reintentar</button>
    </template>

    <WorkshopAgenda v-else-if="view === 'agenda'" :token="token" :is-student="isStudent"
      @expired="emit('expired')" />
    <WalletView v-else-if="view === 'wallet' && isStudent" :token="token" :account-id="account.id"
      :name="account.display_name" @expired="emit('expired')" @academic="view = 'groups'" @shop="view = 'ardy'" />
    <GradeRedemptionView v-else-if="view === 'grade' && gradeCourse" :key="gradeCourse.id"
      :course="gradeCourse" :token="token" :account-id="account.id" :faculty="isFaculty"
      @back="view = 'groups'" @expired="emit('expired')" />
    <ParticipationRanking v-else-if="view === 'ranking'" :token="token" :is-student="isStudent"
      @edit="view = 'ardy'" @expired="emit('expired')" />
    <MyArdyView v-else-if="view === 'ardy' && isStudent" :token="token" @expired="emit('expired')" />
    <Administration v-else-if="isAdmin" :token="token" :account-id="account.id" :courses="courses"
      @changed="loadCourses" @expired="emit('expired')" />
    <section v-else class="groups">
      <h1>Mis grupos</h1>
      <FacultyBudgetView v-if="isFaculty" :token="token" :account-id="account.id"
        @expired="emit('expired')" />
      <p v-if="!courses.length" class="tile state-note">Aún no tienes grupos asignados.</p>
      <article v-for="course in courses" :key="course.id" class="tile group">
        <CalendarDays :size="24" aria-hidden="true" />
        <div><h2>{{ course.title }}</h2><p>{{ course.code }} · Grupo {{ course.section }} · {{ course.term }}</p></div>
        <div class="group-actions">
          <span v-if="course.enrolled" class="badge">Matrícula confirmada</span>
          <button v-if="isFaculty || (isStudent && course.enrolled)" class="button secondary" type="button"
            @click="openGradeRedemption(course)">Canje académico</button>
        </div>
      </article>
      <form v-if="isFaculty && courses.length" class="tile form-stack section-form" @submit.prevent="confirmEnrollment">
        <h2>Confirmar matrícula</h2>
        <label>Grupo
          <select v-model="enrollment.course_id" required>
            <option value="" disabled>Selecciona un grupo</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.title }} · {{ course.section }}</option>
          </select>
        </label>
        <label>Correo institucional del estudiante
          <input v-model.trim="enrollment.email" type="email" required />
        </label>
        <button class="button primary" :disabled="busy">Confirmar matrícula</button>
      </form>
    </section>

    <dialog v-if="dialog" ref="modal" aria-labelledby="dialog-title" @close="dialog = null"
      @cancel="busy && $event.preventDefault()">
      <div class="dialog-head">
        <h2 id="dialog-title">{{ dialog === 'create' ? 'Publicar convocatoria' : dialog === 'apply'
          ? 'Postularme como tallerista' : dialog === 'schedule' ? 'Agendar taller' : 'Postulaciones' }}</h2>
        <button type="button" class="icon-button" aria-label="Cerrar" :disabled="busy" @click="closeDialog">
          <X :size="24" aria-hidden="true" />
        </button>
      </div>
      <p v-if="selected" class="dialog-context">{{ selected.title }}</p>
      <p v-if="modalError" role="alert" class="error">{{ modalError }}</p>
      <form v-if="dialog === 'create'" class="form-stack" @submit.prevent="submitCall">
        <label>Grupo
          <select v-model="publish.course_id" required>
            <option value="" disabled>Selecciona un grupo</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.title }} · {{ course.section }}</option>
          </select>
        </label>
        <label>Título <input v-model.trim="publish.title" maxlength="100" required /></label>
        <label>Qué debe enseñar el tallerista
          <textarea v-model.trim="publish.description" minlength="10" maxlength="1800" rows="4" required></textarea>
        </label>
        <button class="button primary" :disabled="busy">Publicar</button>
      </form>
      <form v-else-if="dialog === 'apply'" class="form-stack" @submit.prevent="submitApplication">
        <label>¿Cómo orientarías el taller?
          <textarea v-model.trim="submission.proposal" minlength="10" maxlength="1800" rows="4" required></textarea>
        </label>
        <label>Enlace a evidencia (opcional)
          <input v-model.trim="submission.evidence_url" type="url" placeholder="https://…" />
        </label>
        <button class="button primary" :disabled="busy">Enviar postulación</button>
      </form>
      <form v-else-if="dialog === 'schedule'" class="form-stack" @submit.prevent="scheduleWorkshop">
        <p class="state-note">Usa la hora de Colombia.</p>
        <label>Inicio del taller <input v-model="schedule.starts_at" type="datetime-local" required /></label>
        <label>Fin del taller <input v-model="schedule.ends_at" type="datetime-local" required /></label>
        <label>Lugar <input v-model.trim="schedule.location" maxlength="160" required /></label>
        <label>Cupos <input v-model.number="schedule.capacity" type="number" min="1" max="300" step="1" required /></label>
        <button class="button primary" :disabled="busy">Publicar en agenda</button>
      </form>
      <template v-else>
        <p v-if="!applications.length && !modalError" class="state-note">Aún no hay postulaciones.</p>
        <article v-for="application in applications" :key="application.id" class="tile application">
          <h3>{{ application.display_name }}</h3>
          <p>{{ application.proposal }}</p>
          <a v-if="application.evidence_url" :href="application.evidence_url" target="_blank" rel="noopener noreferrer">Abrir evidencia</a>
          <button v-if="application.status === 'pending'" class="button secondary" :disabled="busy"
            @click="approveApplication(application)">Aprobar tallerista</button>
          <span v-else class="badge">{{ statusLabels[application.status] }}</span>
        </article>
      </template>
    </dialog>
  </main>
</template>
