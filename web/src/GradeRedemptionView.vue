<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowLeft, GraduationCap, History, Save } from '@lucide/vue'
import {
  api, errorText, RequestError, type GradeCourse, type GradeRedemption,
  type GradeRequest, type GradeRosterEntry, type GradeRule, type GradeRuleInput,
} from './client'

const props = defineProps<{ token: string; accountId: string; course: GradeCourse; faculty: boolean }>()
const emit = defineEmits<{ expired: []; back: [] }>()

const path = `/courses/${props.course.id}/grade-redemption`
const storageKey = `wallnut.pending-grade-redemption.${props.accountId}.${props.course.id}`
const group = ref<GradeRedemption>()
const catalog = ref<GradeCourse[]>([])
const loading = ref(false)
const saving = ref(false)
const notice = ref('')
const problem = ref('')
const rosterGrades = reactive<Record<string, string>>({})
const rejection = ref('')
const reason = ref('')
const steps = ref<number | ''>(1)
const ruleInput = reactive({
  assessment: '',
  points_per_step: '' as number | '',
  step: '',
  maxBonus: '',
  minimum: '',
  sources: [props.course.id],
})

const labels = {
  pending: 'En revisión',
  approved: 'Aprobada',
  rejected: 'Rechazada',
}
const grades = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 3 })
const numbers = new Intl.NumberFormat('es-CO')
const dates = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'America/Bogota' })

interface PendingRequest {
  request_id: string
  steps: number
}

function restoreRequest(): PendingRequest | null {
  if (props.faculty) return null
  try {
    const saved = sessionStorage.getItem(storageKey)
    if (!saved) return null
    const item: PendingRequest = JSON.parse(saved)
    return typeof item?.request_id === 'string' && Number.isSafeInteger(item.steps) && item.steps > 0
      ? item : null
  } catch {
    return null
  }
}

const pending = ref(restoreRequest())
if (pending.value) steps.value = pending.value.steps

function rememberRequest(value: PendingRequest | null) {
  pending.value = value
  try {
    if (value) sessionStorage.setItem(storageKey, JSON.stringify(value))
    else sessionStorage.removeItem(storageKey)
  } catch {
    // El mismo identificador sigue disponible en esta vista.
  }
}

function formatGrade(value: number | null | undefined) {
  return value == null ? 'Sin registrar' : grades.format(value / 1000)
}

function gradeInput(value: number | null | undefined) {
  return value == null ? '' : grades.format(value / 1000)
}

function parseMilli(value: string): number | null {
  const match = /^(\d)(?:[.,](\d{1,3}))?$/.exec(value.trim())
  if (!match?.[1]) return null
  const milli = Number(match[1]) * 1000 + Number((match[2] ?? '').padEnd(3, '0'))
  return milli <= 5000 ? milli : null
}

function displayCourse(course: GradeCourse) {
  return `${course.title} · ${course.code} · Grupo ${course.section} · ${course.term}`
}

function handleError(error: unknown) {
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else problem.value = errorText(error)
}

function fillRule(rule: GradeRule | null) {
  ruleInput.assessment = rule?.assessment ?? ''
  ruleInput.points_per_step = rule?.points_per_step ?? ''
  ruleInput.step = gradeInput(rule?.step_milli)
  ruleInput.maxBonus = gradeInput(rule?.max_bonus_milli)
  ruleInput.minimum = gradeInput(rule?.minimum_grade_milli)
  ruleInput.sources = rule?.accepted_course_ids ? [...rule.accepted_course_ids] : [props.course.id]
}

async function load() {
  if (loading.value) return
  loading.value = true
  problem.value = ''
  try {
    const data = await api<GradeRedemption>(path, { token: props.token })
    if (props.faculty) {
      catalog.value = await api<GradeCourse[]>('/grade-redemptions/courses', { token: props.token })
      fillRule(data.rule)
      for (const member of data.roster) {
        rosterGrades[member.student_id] = gradeInput(member.base_grade_milli)
      }
    }
    group.value = data
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function run(action: () => Promise<unknown>, success: string) {
  if (saving.value) return
  saving.value = true
  problem.value = ''
  notice.value = ''
  try {
    await action()
    notice.value = success
    await load()
  } catch (error) {
    handleError(error)
  } finally {
    saving.value = false
  }
}

function saveRule() {
  const step = parseMilli(ruleInput.step)
  const maxBonus = parseMilli(ruleInput.maxBonus)
  const minimum = parseMilli(ruleInput.minimum)
  if (step === null || step <= 0 || maxBonus === null || maxBonus < step
      || (ruleInput.minimum.trim() !== '' && minimum === null)) {
    problem.value = 'Usa valores entre 0 y 5 con hasta tres decimales. El tope debe alcanzar al menos un incremento.'
    return
  }
  if (!ruleInput.sources.length || ruleInput.sources.length > 100) {
    problem.value = 'Selecciona entre 1 y 100 grupos de origen.'
    return
  }
  const data: GradeRuleInput = {
    assessment: ruleInput.assessment,
    points_per_step: Number(ruleInput.points_per_step),
    step_milli: step,
    max_bonus_milli: maxBonus,
    minimum_grade_milli: minimum,
    accepted_course_ids: ruleInput.sources,
  }
  return run(() => api(`${path}/rule`, { token: props.token, method: 'PUT', data }), 'Regla de canje guardada.')
}

function saveBase(member: GradeRosterEntry) {
  const value = parseMilli(rosterGrades[member.student_id] ?? '')
  if (value === null) {
    problem.value = 'Ingresa una nota entre 0 y 5 con hasta tres decimales.'
    return
  }
  return run(() => api(`${path}/students/${member.student_id}`, {
    token: props.token, method: 'PUT', data: { base_grade_milli: value },
  }), 'Nota base simulada guardada.')
}

const pendingOnServer = computed(() => group.value?.requests.some((item) => item.status === 'pending') ?? false)
const belowMinimum = computed(() => {
  const minimum = group.value?.rule?.minimum_grade_milli
  const base = group.value?.student?.base_grade_milli
  return minimum != null && base != null && base < minimum
})
const maxSteps = computed(() => {
  const student = group.value?.student
  const rule = group.value?.rule
  if (!rule || !student || student.simulated_grade_milli == null
      || student.base_grade_milli == null || belowMinimum.value || pendingOnServer.value) return 0
  const remainingBoost = Math.min(student.remaining_bonus_milli, 5000 - student.simulated_grade_milli)
  return Math.max(0, Math.min(
    Math.floor(student.eligible_points / rule.points_per_step),
    Math.floor(remainingBoost / rule.step_milli),
  ))
})
const validSteps = computed(() =>
  Number.isSafeInteger(steps.value) && Number(steps.value) > 0 && Number(steps.value) <= maxSteps.value,
)
const requestedPoints = computed(() => Number(steps.value) * (group.value?.rule?.points_per_step ?? 0))
const requestedBoost = computed(() => Number(steps.value) * (group.value?.rule?.step_milli ?? 0))

function submitRequest() {
  if (saving.value || (!pending.value && !validSteps.value)) return
  const request = pending.value ?? { request_id: crypto.randomUUID(), steps: Number(steps.value) }
  rememberRequest(request)
  return run(async () => {
    try {
      await api(`${path}/requests`, { token: props.token, method: 'POST', data: request })
      rememberRequest(null)
      steps.value = 1
    } catch (error) {
      if (error instanceof RequestError && [400, 403, 404, 409, 422].includes(error.status)) {
        rememberRequest(null)
      }
      throw error
    }
  }, 'Solicitud enviada. Los Points quedan reservados hasta la revisión.')
}

function review(request: GradeRequest, decision: 'approved' | 'rejected') {
  return run(async () => {
    await api(`${path}/requests/${request.id}/review`, {
      token: props.token, method: 'PUT',
      data: { decision, reason: decision === 'rejected' ? reason.value.trim() : null },
    })
    rejection.value = ''
    reason.value = ''
  }, decision === 'approved' ? 'Canje aprobado y nota simulada actualizada.' : 'Solicitud rechazada. Los Points volvieron al saldo disponible.')
}
</script>

<template>
  <section class="economy-page grade-page" aria-labelledby="grade-heading">
    <button class="button quiet grade-back" type="button" @click="emit('back')">
      <ArrowLeft :size="17" aria-hidden="true" /> Volver a Mis grupos
    </button>
    <div class="section-heading">
      <div>
        <h1 id="grade-heading">Canje académico</h1>
        <p>{{ displayCourse(course) }}</p>
      </div>
      <span class="badge">Simulación</span>
    </div>

    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="loading && !group" class="state-note" role="status">Consultando el grupo…</p>
    <button v-if="problem && !group" class="button secondary" type="button" @click="load">Volver a consultar</button>

    <template v-if="group">
      <section v-if="faculty" class="tile grade-section grade-rule" aria-labelledby="grade-rule-heading">
        <h2 id="grade-rule-heading">Regla del grupo</h2>
        <p v-if="group.rule?.locked">La regla está vinculada a solicitudes pendientes o aprobadas.</p>
        <form class="form-stack" @submit.prevent="saveRule">
          <fieldset :disabled="saving || loading || group.rule?.locked">
            <label>Evaluación simulada
              <input v-model.trim="ruleInput.assessment" placeholder="Ej. Primer corte" maxlength="100" required />
            </label>
            <div class="economy-fields">
              <label>Points por incremento
                <input v-model.number="ruleInput.points_per_step" type="number" min="1" max="1000000" step="1" required />
              </label>
              <label>Incremento de nota
                <input v-model.trim="ruleInput.step" inputmode="decimal" maxlength="5" placeholder="0,10" required />
              </label>
              <label>Tope total de mejora
                <input v-model.trim="ruleInput.maxBonus" inputmode="decimal" maxlength="5" placeholder="0,30" required />
              </label>
              <label>Nota base mínima (opcional)
                <input v-model.trim="ruleInput.minimum" inputmode="decimal" maxlength="5" placeholder="3,80" />
              </label>
            </div>
            <div class="source-list" role="group" aria-label="Grupos de origen aceptados">
              <h3>Grupos de origen aceptados</h3>
              <label v-for="origin in catalog" :key="origin.id" class="check-label">
                <input v-model="ruleInput.sources" type="checkbox" :value="origin.id" />
                <span>{{ displayCourse(origin) }}</span>
              </label>
            </div>
            <button v-if="!group.rule?.locked" class="button primary" type="submit">Guardar regla</button>
          </fieldset>
        </form>
      </section>

      <section v-if="faculty" class="grade-section" aria-labelledby="grade-roster-heading">
        <h2 id="grade-roster-heading">Notas base simuladas</h2>
        <p v-if="!group.roster.length" class="tile state-note">Confirma la matrícula de estudiantes para registrar sus notas base.</p>
        <ul v-else class="tile grade-roster">
          <li v-for="member in group.roster" :key="member.student_id">
            <div>
              <h3>{{ member.display_name }}</h3>
              <p class="wallet-context">{{ member.email }}</p>
            </div>
            <form class="form-stack grade-roster-form" @submit.prevent="saveBase(member)">
              <label>Nota base de {{ member.display_name }}
                <input v-model.trim="rosterGrades[member.student_id]" inputmode="decimal" maxlength="5" placeholder="0,00"
                  :disabled="saving || loading || member.locked" required />
              </label>
              <span v-if="member.locked" class="badge">Vinculada a un canje</span>
              <button v-else type="submit" class="button secondary" :disabled="saving || loading">Guardar nota</button>
            </form>
          </li>
        </ul>
      </section>

      <template v-else>
        <p v-if="!group.rule" class="tile state-note">El docente aún no ha configurado el canje para este grupo.</p>
        <section v-else class="tile grade-section" aria-labelledby="grade-summary-heading">
          <h2 id="grade-summary-heading">{{ group.rule.assessment }}</h2>
          <p class="grade-equivalent">
            {{ numbers.format(group.rule.points_per_step) }} Points por +{{ formatGrade(group.rule.step_milli) }}
          </p>
          <dl class="grade-metrics">
            <div><dt>Nota base</dt><dd>{{ formatGrade(group.student?.base_grade_milli) }}</dd></div>
            <div><dt>Nota simulada actual</dt><dd>{{ formatGrade(group.student?.simulated_grade_milli) }}</dd></div>
            <div><dt>Points válidos para el grupo</dt><dd>{{ numbers.format(group.student?.eligible_points ?? 0) }}</dd></div>
            <div><dt>Tope restante</dt><dd>+{{ formatGrade(group.student?.remaining_bonus_milli ?? 0) }}</dd></div>
          </dl>
          <p v-if="group.rule.minimum_grade_milli !== null">Nota base mínima: {{ formatGrade(group.rule.minimum_grade_milli) }}.</p>
          <p v-if="pendingOnServer" class="state-note">Tienes una solicitud pendiente de revisión.</p>
          <p v-else-if="group.student?.base_grade_milli == null" class="state-note">El docente aún no ha registrado tu nota base simulada.</p>
          <p v-else-if="belowMinimum" class="state-note">Tu nota base no alcanza el mínimo de este grupo.</p>
          <p v-else-if="!maxSteps" class="state-note">
            {{ (group.student?.eligible_points ?? 0) < group.rule.points_per_step
              ? 'Te faltan Points de un origen aceptado para solicitar el ajuste.'
              : 'El tope restante o la nota máxima no permiten otro incremento.' }}
          </p>

          <form v-if="maxSteps || pending" class="form-stack grade-request-form" @submit.prevent="submitRequest">
            <p v-if="pending && !saving" class="state-note">Hay una solicitud por confirmar. Reintenta con los mismos datos.</p>
            <label>Incrementos que quieres solicitar
              <input v-model.number="steps" type="number" min="1" :max="pending ? undefined : maxSteps" step="1"
                :disabled="saving || !!pending" required />
            </label>
            <p v-if="validSteps">
              Se reservan <strong>{{ numbers.format(requestedPoints) }} Points</strong> para un ajuste de
              <strong>+{{ formatGrade(requestedBoost) }}</strong>.
              Nota resultante: <strong>{{ formatGrade((group.student?.simulated_grade_milli ?? 0) + requestedBoost) }}</strong>.
            </p>
            <button class="button primary" type="submit" :disabled="saving || (!pending && !validSteps)">
              {{ saving ? 'Enviando…' : pending ? 'Confirmar solicitud pendiente' : 'Solicitar ajuste' }}
            </button>
          </form>
        </section>
      </template>

      <section class="grade-section" aria-labelledby="grade-requests-heading">
        <h2 id="grade-requests-heading"><History :size="21" aria-hidden="true" /> {{ faculty ? 'Solicitudes del grupo' : 'Mis solicitudes' }}</h2>
        <p v-if="!group.requests.length" class="tile state-note">Aún no hay solicitudes de ajuste.</p>
        <article v-for="item in group.requests" :key="item.id" class="tile grade-review">
          <div class="evidence-heading">
            <h3 v-if="faculty">{{ item.display_name }}</h3>
            <strong v-else>+{{ formatGrade(item.boost_milli) }} en la nota</strong>
            <span :class="['badge', { 'badge-confirmed': item.status === 'approved' }]">{{ labels[item.status] }}</span>
          </div>
          <p>{{ item.assessment }} · {{ formatGrade(item.grade_before_milli) }} a {{ formatGrade(item.grade_after_milli) }} · {{ numbers.format(item.points) }} Points</p>
          <p v-if="item.reason" class="reflection">{{ item.reason }}</p>
          <time class="wallet-context" :datetime="item.created_at">{{ dates.format(new Date(item.created_at)) }}</time>
          <div v-if="faculty && item.status === 'pending' && rejection !== item.id" class="workshop-actions">
            <button class="button primary" type="button" :disabled="saving || loading" @click="review(item, 'approved')">Aprobar ajuste</button>
            <button class="button secondary" type="button" :disabled="saving || loading"
              @click="rejection = item.id; reason = ''">Rechazar ajuste</button>
          </div>
          <form v-if="faculty && item.status === 'pending' && rejection === item.id" class="form-stack" @submit.prevent="review(item, 'rejected')">
            <label>Motivo del rechazo
              <textarea v-model.trim="reason" rows="3" maxlength="1000" required></textarea>
            </label>
            <div class="workshop-actions">
              <button class="button primary" type="submit" :disabled="saving || loading || !reason">Confirmar rechazo</button>
              <button class="button quiet" type="button" :disabled="saving" @click="rejection = ''">Cancelar</button>
            </div>
          </form>
        </article>
      </section>
    </template>
  </section>
</template>
