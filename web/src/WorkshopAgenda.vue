<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { CalendarDays, Camera, ClipboardCheck, Clock, MapPin, QrCode, Target, UserRound, Users, X } from '@lucide/vue'
import QrScanner from './QrScanner.vue'
import WorkshopEconomyView from './WorkshopEconomyView.vue'
import WorkshopEvidence from './WorkshopEvidence.vue'
import { api, errorText, RequestError, type Attendance, type AttendanceCode, type Workshop } from './client'

const props = defineProps<{ token: string; isStudent: boolean }>()
const emit = defineEmits<{ expired: [] }>()
type Dialog = 'code' | 'check-in' | 'evidence' | 'economy'
const workshops = ref<Workshop[]>([])
const loading = ref(false)
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const selection = ref<Workshop>()
const dialog = ref<Dialog | null>(null)
const modal = ref<HTMLDialogElement>()
const modalProblem = ref('')
const attendanceCode = ref<AttendanceCode>()
const qrImage = ref('')
const inputCode = ref('')
const scanning = ref(false)
const currentTime = ref(Date.now())
const dayFormat = new Intl.DateTimeFormat('es-CO', {
  weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'America/Bogota',
})
const hourFormat = new Intl.DateTimeFormat('es-CO', {
  hour: 'numeric', minute: '2-digit', timeZone: 'America/Bogota',
})
let timer: ReturnType<typeof setInterval>

function started(workshop: Workshop) { return currentTime.value >= Date.parse(workshop.starts_at) }
function ended(workshop: Workshop) { return currentTime.value >= Date.parse(workshop.ends_at) }
function codeIsValid(code?: AttendanceCode) { return !!code && currentTime.value < Date.parse(code.expires_at) }

function handleError(error: unknown, target: typeof problem) {
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else target.value = errorText(error)
}

async function load() {
  if (loading.value) return
  loading.value = true
  problem.value = ''
  try {
    workshops.value = await api<Workshop[]>('/workshops', { token: props.token })
  } catch (error) {
    handleError(error, problem)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  timer = setInterval(() => { currentTime.value = Date.now() }, 1000)
  void load()
})
onBeforeUnmount(() => clearInterval(timer))

async function changeEnrollment(workshop: Workshop) {
  if (busy.value || loading.value) return
  busy.value = true
  notice.value = ''
  problem.value = ''
  try {
    await api(`/workshops/${workshop.id}/enrollment`, {
      token: props.token, method: workshop.enrolled ? 'DELETE' : 'PUT',
    })
    notice.value = workshop.enrolled ? 'Inscripción cancelada.' : 'Inscripción confirmada.'
    await load()
  } catch (error) {
    handleError(error, problem)
  } finally {
    busy.value = false
  }
}

async function openDialog(workshop: Workshop, mode: Dialog) {
  selection.value = workshop
  dialog.value = mode
  attendanceCode.value = undefined
  qrImage.value = ''
  inputCode.value = ''
  modalProblem.value = ''
  scanning.value = false
  await nextTick()
  modal.value?.showModal()
}

function clearDialog() {
  scanning.value = false
  dialog.value = null
  selection.value = undefined
}

async function generateCode() {
  const workshop = selection.value
  if (!workshop || busy.value) return
  busy.value = true
  modalProblem.value = ''
  try {
    const code = await api<AttendanceCode>(`/workshops/${workshop.id}/attendance-code`, {
      token: props.token, method: 'POST',
    })
    attendanceCode.value = code
    qrImage.value = ''
    const { toDataURL } = await import('qrcode')
    qrImage.value = await toDataURL(code.qr_value, { width: 264, margin: 3 })
  } catch (error) {
    handleError(error, modalProblem)
  } finally {
    busy.value = false
  }
}

async function checkIn(value: string) {
  const workshop = selection.value
  if (!workshop || busy.value) return
  scanning.value = false
  const code = value.trim().toUpperCase().replace(/\s+/g, '')
  if (!/^[A-Z0-9]{8}$/.test(code)) {
    modalProblem.value = 'Ingresa las ocho letras o números del código.'
    return
  }
  inputCode.value = code
  busy.value = true
  modalProblem.value = ''
  try {
    const attendance = await api<Attendance>(`/workshops/${workshop.id}/attendance`, {
      token: props.token, method: 'POST', data: { code },
    })
    notice.value = attendance.already_recorded ? 'Tu asistencia ya estaba registrada.' : 'Asistencia registrada.'
    modal.value?.close()
    await load()
  } catch (error) {
    handleError(error, modalProblem)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="workshop-agenda" aria-labelledby="agenda-heading">
    <div class="section-heading">
      <div>
        <h1 id="agenda-heading">Agenda de talleres</h1>
        <p>Horarios de Colombia</p>
      </div>
      <button v-if="workshops.length" class="button quiet" type="button" :disabled="loading || busy" @click="load">
        Actualizar agenda
      </button>
    </div>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <button v-if="problem && !workshops.length" class="button secondary" type="button" @click="load">Reintentar</button>
    <p v-if="loading && !workshops.length" class="state-note" role="status">Cargando talleres…</p>
    <p v-else-if="!workshops.length && !problem" class="tile state-note">Aún no hay talleres agendados.</p>
    <div class="feed-list">
      <article v-for="workshop in workshops" :key="workshop.id" class="tile call-card agenda-card">
        <div class="call-icon"><CalendarDays :size="25" aria-hidden="true" /></div>
        <div class="call-content">
          <div class="call-meta">
            <span>{{ workshop.course }}</span>
            <span v-if="workshop.attended" class="badge badge-confirmed">Asistencia registrada</span>
            <span v-else-if="workshop.enrolled" class="badge badge-confirmed">Inscripción confirmada</span>
            <span v-else-if="workshop.is_facilitator" class="badge badge-confirmed">Soy tallerista</span>
            <span v-else-if="started(workshop) && !ended(workshop)" class="badge">En curso</span>
            <span v-else-if="ended(workshop)" class="badge">Finalizado</span>
          </div>
          <h2>{{ workshop.title }}</h2>
          <ul class="workshop-meta">
            <li><CalendarDays :size="17" aria-hidden="true" /> <time :datetime="workshop.starts_at">{{ dayFormat.format(new Date(workshop.starts_at)) }}</time></li>
            <li><Clock :size="17" aria-hidden="true" /> {{ hourFormat.format(new Date(workshop.starts_at)) }} – {{ hourFormat.format(new Date(workshop.ends_at)) }}</li>
            <li><MapPin :size="17" aria-hidden="true" /> {{ workshop.location }}</li>
            <li><UserRound :size="17" aria-hidden="true" /> {{ workshop.facilitator_name }}</li>
            <li><Users :size="17" aria-hidden="true" /> {{ workshop.enrolled_count }} de {{ workshop.capacity }} cupos ocupados</li>
          </ul>
          <div class="workshop-actions">
            <template v-if="isStudent && !workshop.is_facilitator">
              <button v-if="!started(workshop) && workshop.enrolled" type="button" class="button quiet"
                :disabled="busy || loading" @click="changeEnrollment(workshop)">Cancelar inscripción</button>
              <button v-else-if="!started(workshop) && workshop.enrolled_count < workshop.capacity" type="button"
                class="button primary" :disabled="busy || loading" @click="changeEnrollment(workshop)">Inscribirme</button>
              <p v-else-if="!started(workshop)" class="state-note">Sin cupos disponibles.</p>
              <button v-if="workshop.enrolled && !workshop.attended && started(workshop) && !ended(workshop)"
                type="button" class="button primary" :disabled="busy" @click="openDialog(workshop, 'check-in')">
                <QrCode :size="18" aria-hidden="true" /> Registrar asistencia
              </button>
            </template>
            <button v-if="workshop.can_issue_code && started(workshop) && !ended(workshop)" type="button" class="button secondary"
              :disabled="busy" @click="openDialog(workshop, 'code')"><QrCode :size="18" aria-hidden="true" /> QR y código</button>
            <button v-if="workshop.attended || workshop.can_manage || (workshop.is_facilitator && started(workshop))"
              type="button" class="button secondary" :disabled="busy" @click="openDialog(workshop, 'evidence')">
              <ClipboardCheck :size="18" aria-hidden="true" /> {{ workshop.can_manage ? 'Revisar evidencias' : 'Mi evidencia' }}
            </button>
            <button type="button" class="button quiet" :disabled="busy" @click="openDialog(workshop, 'economy')">
              <Target :size="18" aria-hidden="true" />
              {{ workshop.can_manage ? 'Configurar recompensas' : 'Ver recompensas' }}
            </button>
          </div>
        </div>
      </article>
    </div>

    <dialog v-if="dialog && selection" ref="modal" aria-labelledby="workshop-dialog-title" @close="clearDialog"
      @cancel="busy && $event.preventDefault()">
      <div class="dialog-head">
        <h2 id="workshop-dialog-title">{{ dialog === 'code' ? 'QR y código de asistencia' : dialog === 'check-in'
          ? 'Registrar asistencia' : dialog === 'economy' ? 'Recompensas del taller'
            : selection.can_manage ? 'Revisar evidencias' : 'Mi evidencia' }}</h2>
        <button type="button" class="icon-button" aria-label="Cerrar" :disabled="busy" @click="modal?.close()">
          <X :size="24" aria-hidden="true" />
        </button>
      </div>
      <p class="dialog-context">{{ selection.title }}</p>
      <p v-if="modalProblem" class="error" role="alert">{{ modalProblem }}</p>
      <section v-if="dialog === 'code'" class="form-stack">
        <div v-if="attendanceCode && codeIsValid(attendanceCode)" class="check-in-token">
          <img v-if="qrImage" :src="qrImage" alt="Código QR de asistencia del taller" width="264" height="264" />
          <p>Código manual <strong>{{ attendanceCode.code }}</strong></p>
          <p>Vence a las {{ hourFormat.format(new Date(attendanceCode.expires_at)) }}.</p>
        </div>
        <p v-else-if="attendanceCode" class="state-note" role="status">El código venció.</p>
        <p v-else>Muestra el QR o comparte el código con los asistentes presentes.</p>
        <button class="button primary" type="button" :disabled="busy || ended(selection)" @click="generateCode">
          {{ attendanceCode ? 'Renovar QR y código' : 'Generar QR y código' }}
        </button>
      </section>
      <section v-else-if="dialog === 'check-in'">
        <QrScanner v-if="scanning" instruction="Enfoca el QR del taller con la cámara."
          mismatch="Este QR no corresponde al taller. Escanea el QR que presenta tu tallerista."
          :parse="value => value.match(new RegExp(`^wallnut:attendance:${selection?.id}:([A-Z0-9]{8})$`))?.[1]"
          @close="scanning = false" @code="checkIn" />
        <form v-else class="form-stack" @submit.prevent="checkIn(inputCode)">
          <button type="button" class="button secondary" :disabled="busy" @click="modalProblem = ''; scanning = true">
            <Camera :size="18" aria-hidden="true" /> Escanear QR
          </button>
          <label>Código del taller
            <input v-model.trim="inputCode" required maxlength="16" autocomplete="off" autocapitalize="characters"
              spellcheck="false" aria-describedby="attendance-code-hint" />
          </label>
          <p id="attendance-code-hint">El docente o tallerista te comparte el código de ocho caracteres.</p>
          <button class="button primary" type="submit" :disabled="busy">Registrar asistencia</button>
        </form>
      </section>
      <WorkshopEconomyView v-else-if="dialog === 'economy'" :workshop="selection" :token="token"
        @expired="emit('expired')" />
      <WorkshopEvidence v-else :workshop="selection" :token="token" @expired="emit('expired')" />
    </dialog>
  </section>
</template>
