<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api, apiPhoto, errorText, RequestError, type Workshop, type WorkshopEconomy, type WorkshopEvidence } from './client'

const props = defineProps<{ workshop: Workshop; token: string }>()
const emit = defineEmits<{ expired: [] }>()
const items = ref<WorkshopEvidence[]>([])
const economy = ref<WorkshopEconomy | null>()
const reflection = ref('')
const photo = ref<File>()
const fileInput = ref<HTMLInputElement>()
const photoUrl = ref('')
const photoFor = ref('')
const photoLoading = ref(false)
const loading = ref(true)
const loaded = ref(false)
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const returning = ref('')
const comment = ref('')
let active = true
const basePath = `/workshops/${props.workshop.id}/evidence`

const states = {
  submitted: 'Pendiente de revisión',
  returned: 'Devuelta para corregir',
  approved: 'Aprobada',
}

function handleError(error: unknown) {
  if (!active) return
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else problem.value = errorText(error)
}

async function load() {
  loading.value = true
  problem.value = ''
  try {
    items.value = await api<WorkshopEvidence[]>(basePath, { token: props.token })
    loaded.value = true
    if (!props.workshop.can_manage) reflection.value = items.value[0]?.reflection ?? ''
    if (economy.value === undefined) {
      economy.value = await api<WorkshopEconomy | null>(`/workshops/${props.workshop.id}/economy`, { token: props.token })
    }
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

function clearPhoto() {
  if (photoUrl.value) URL.revokeObjectURL(photoUrl.value)
  photoUrl.value = ''
  photoFor.value = ''
}
onMounted(load)
onBeforeUnmount(() => {
  active = false
  clearPhoto()
})

function selectPhoto(event: Event) {
  photo.value = (event.target as HTMLInputElement).files?.[0]
}

async function showPhoto(item: WorkshopEvidence) {
  if (photoLoading.value) return
  const showingSame = photoFor.value === item.id
  clearPhoto()
  if (showingSame) return
  photoLoading.value = true
  problem.value = ''
  try {
    const image = await apiPhoto(`${basePath}/${item.id}/photo`, props.token)
    if (!active) return
    photoUrl.value = URL.createObjectURL(image)
    photoFor.value = item.id
  } catch (error) {
    handleError(error)
  } finally {
    photoLoading.value = false
  }
}

async function submit() {
  if (busy.value || !photo.value || !reflection.value.trim()) return
  if (photo.value.size > 8 * 1024 * 1024) {
    problem.value = 'La foto debe pesar 8 MB o menos.'
    return
  }
  busy.value = true
  problem.value = ''
  notice.value = ''
  const data = new FormData()
  data.set('photo', photo.value)
  data.set('reflection', reflection.value)
  try {
    const result = await api<WorkshopEvidence>(basePath, { token: props.token, method: 'POST', data })
    clearPhoto()
    photo.value = undefined
    if (fileInput.value) fileInput.value.value = ''
    items.value = [result]
    notice.value = 'Evidencia enviada para revisión.'
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}

function startReturn(item: WorkshopEvidence) {
  returning.value = item.id
  comment.value = ''
}

async function review(item: WorkshopEvidence, decision: 'approved' | 'returned') {
  if (busy.value || (decision === 'returned' && !comment.value.trim())) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    const updated = await api<WorkshopEvidence>(`${basePath}/${item.id}/review`, {
      token: props.token, method: 'PUT',
      data: { decision, submitted_at: item.submitted_at, comment: decision === 'returned' ? comment.value : null },
    })
    items.value = items.value.map((entry) => entry.id === updated.id ? updated : entry)
    returning.value = ''
    if (decision === 'returned') notice.value = 'Evidencia devuelta para corregir.'
    else if (updated.points_awarded) notice.value = `Evidencia aprobada. Se acreditaron ${updated.points_awarded} Points.`
    else if (updated.reward_points) notice.value = 'Evidencia aprobada. Los Points están pendientes de acreditar.'
    else notice.value = 'Evidencia aprobada.'
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}

async function award(item: WorkshopEvidence, kind: 'reward' | 'goal') {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    await api(`${basePath}/${item.id}/${kind}`, { token: props.token, method: 'POST' })
    notice.value = kind === 'goal' ? 'Meta verificada y Coins acreditados.' : 'Points acreditados desde tu cupo.'
    await load()
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="evidence-panel">
    <p v-if="loading" class="state-note" role="status">Cargando evidencias…</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <button v-if="!loading && problem" class="button quiet" type="button" @click="load">Volver a consultar</button>
    <p v-if="workshop.can_manage && !loading && !problem && !items.length" class="state-note">Aún no hay evidencias.</p>
    <div v-if="economy?.goal_description" class="tile workshop-goal">
      <h3>Meta académica</h3>
      <p class="reflection">{{ economy.goal_description }}</p>
      <p>{{ economy.goal_coins }} Coins al verificar · Canje de {{ economy.coin_cost }} Coins por {{ economy.conversion_points }} Points</p>
    </div>
    <article v-for="item in items" :key="item.id" class="tile evidence-item">
      <div class="evidence-heading">
        <h3>{{ workshop.can_manage ? item.display_name : 'Tu entrega' }}</h3>
        <span :class="['badge', { 'badge-confirmed': item.status === 'approved' }]">{{ states[item.status] }}</span>
        <span v-if="item.points_awarded" class="badge badge-confirmed">+{{ item.points_awarded }} Points</span>
        <span v-else-if="item.status === 'approved' && item.reward_points" class="badge">Points pendientes</span>
        <span v-if="item.goal_verified" class="badge badge-confirmed">Meta verificada</span>
      </div>
      <p class="reflection">{{ item.reflection }}</p>
      <p v-if="item.comment"><strong>Retroalimentación:</strong> {{ item.comment }}</p>
      <img v-if="photoFor === item.id && photoUrl" :src="photoUrl" alt="Foto adjunta a la evidencia" class="evidence-photo" />
      <div class="workshop-actions">
        <button class="button quiet" type="button" :disabled="photoLoading" @click="showPhoto(item)">
          {{ photoFor === item.id ? 'Ocultar foto' : 'Ver foto' }}
        </button>
        <template v-if="workshop.can_manage && item.status === 'submitted' && returning !== item.id">
          <button class="button primary" type="button" :disabled="busy" @click="review(item, 'approved')">Aprobar evidencia</button>
          <button class="button secondary" type="button" :disabled="busy" @click="startReturn(item)">Devolver para corregir</button>
        </template>
        <template v-if="workshop.can_manage && item.status === 'approved'">
          <button v-if="item.reward_points > item.points_awarded" class="button secondary" type="button" :disabled="busy"
            @click="award(item, 'reward')">Acreditar Points</button>
          <button v-if="economy?.goal_description && !item.goal_verified" class="button primary" type="button" :disabled="busy"
            @click="award(item, 'goal')">Verificar meta y otorgar Coins</button>
        </template>
      </div>
      <form v-if="workshop.can_manage && item.status === 'submitted' && returning === item.id"
        class="form-stack" @submit.prevent="review(item, 'returned')">
        <label>Comentario para el estudiante
          <textarea v-model.trim="comment" rows="3" maxlength="1000" required></textarea>
        </label>
        <div class="workshop-actions">
          <button class="button primary" type="submit" :disabled="busy">Devolver evidencia</button>
          <button class="button quiet" type="button" :disabled="busy" @click="returning = ''">Cancelar</button>
        </div>
      </form>
    </article>
    <form v-if="!workshop.can_manage && loaded && !loading && (items.length === 0 || items[0]?.status === 'returned')"
      class="form-stack evidence-form" @submit.prevent="submit">
      <label>{{ items[0]?.status === 'returned' ? 'Foto corregida' : 'Foto de tu trabajo' }}
        <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" required @change="selectPhoto" />
      </label>
      <p>JPG, PNG o WebP. Máximo 8 MB.</p>
      <label>¿Qué hiciste durante el taller?
        <textarea v-model.trim="reflection" rows="4" maxlength="2000" required></textarea>
      </label>
      <button class="button primary" type="submit" :disabled="busy">
        {{ items[0]?.status === 'returned' ? 'Reenviar evidencia' : 'Enviar evidencia' }}
      </button>
    </form>
  </section>
</template>
