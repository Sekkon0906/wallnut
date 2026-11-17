<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api, errorText, RequestError } from './client'
import { postDate, postPageSize, type CampusPost, type CampusPostReport } from './campusPosts'
import CampusPostPhoto from './CampusPostPhoto.vue'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ expired: [] }>()
const reports = ref<CampusPostReport[]>([])
const showHidden = ref(false)
const more = ref(false)
const loading = ref(false)
const saving = ref(false)
const problem = ref('')
const decisionError = ref('')
const notice = ref('')
const explanation = ref('')
const dialog = ref<HTMLDialogElement>()
const decision = ref<{ item: CampusPostReport; hide: boolean }>()
let offset = 0
let active = true

function handleError(error: unknown) {
  if (!active) return
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else (dialog.value?.open ? decisionError : problem).value = errorText(error)
}

async function load(append = false) {
  if (loading.value) return
  loading.value = true
  problem.value = ''
  try {
    const from = append ? offset : 0
    const rows = await api<CampusPostReport[]>(`/post-reports?offset=${from}&hidden=${showHidden.value}`, { token: props.token })
    const page = rows.slice(0, postPageSize)
    if (append) {
      const ids = new Set(reports.value.map(row => row.post.id))
      reports.value = [...reports.value, ...page.filter(row => !ids.has(row.post.id))]
    } else reports.value = page
    offset = from + page.length
    more.value = rows.length > postPageSize
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

function filter(hidden: boolean) {
  if (showHidden.value === hidden) return
  showHidden.value = hidden
  reports.value = []
  more.value = false
  notice.value = ''
  void load()
}

async function choose(item: CampusPostReport, hide: boolean) {
  explanation.value = ''
  decisionError.value = ''
  decision.value = { item, hide }
  await nextTick()
  dialog.value?.showModal()
}

function close() {
  if (!saving.value) dialog.value?.close()
}

async function moderate() {
  const current = decision.value
  if (!current || saving.value || !explanation.value.trim()) return
  saving.value = true
  decisionError.value = ''
  notice.value = ''
  try {
    await api<CampusPost>(`/posts/${current.item.post.id}/moderation`, {
      token: props.token,
      method: 'PUT',
      data: { reason: explanation.value.trim(), hidden: current.hide },
    })
    dialog.value?.close()
    notice.value = current.hide ? 'Publicación oculta.' : current.item.post.hidden ? 'Publicación restaurada.' : 'Reportes cerrados.'
    await load()
  } catch (error) {
    handleError(error)
  } finally {
    saving.value = false
  }
}

onMounted(() => load())
onBeforeUnmount(() => { active = false })
</script>

<template>
  <div class="post-moderation">
    <div class="filters" aria-label="Estado de moderación">
      <button class="filter" type="button" :aria-pressed="!showHidden" :disabled="loading || saving" @click="filter(false)">Reportes pendientes</button>
      <button class="filter" type="button" :aria-pressed="showHidden" :disabled="loading || saving" @click="filter(true)">Publicaciones ocultas</button>
    </div>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <button v-if="problem" class="button quiet" type="button" :disabled="loading" @click="load()">Reintentar</button>
    <p v-if="loading" class="state-note" role="status">Cargando reportes…</p>
    <p v-else-if="!reports.length && !problem" class="tile state-note">{{ showHidden ? 'No hay publicaciones ocultas.' : 'No hay reportes pendientes.' }}</p>
    <article v-for="item in reports" :key="item.post.id" class="tile moderation-item">
      <div class="moderation-title">
        <h3>{{ item.post.author }}</h3>
        <span class="badge">{{ item.report_count }} {{ item.report_count === 1 ? 'reporte' : 'reportes' }}</span>
      </div>
      <p v-if="item.post.body" class="post-caption">{{ item.post.body }}</p>
      <CampusPostPhoto v-if="item.post.has_photo" :token="token" :post-id="item.post.id" :version="item.post.updated_at"
        @expired="emit('expired')" />
      <div class="moderation-details">
        <p v-if="item.report_count"><strong>Último reporte</strong> {{ item.latest_reason }}
          <time :datetime="item.latest_at">{{ postDate.format(new Date(item.latest_at)) }}</time>
        </p>
        <p v-if="item.post.moderation_reason"><strong>Decisión registrada</strong> {{ item.post.moderation_reason }}</p>
      </div>
      <div class="workshop-actions">
        <button v-if="!item.post.hidden" class="button secondary" type="button" :disabled="loading || saving"
          @click="choose(item, true)">Ocultar publicación</button>
        <button class="button quiet" type="button" :disabled="loading || saving" @click="choose(item, false)">
          {{ item.post.hidden ? 'Restaurar publicación' : 'Cerrar reportes' }}
        </button>
      </div>
    </article>
    <button v-if="more" class="button secondary" type="button" :disabled="loading || saving" @click="load(true)">Cargar más reportes</button>
    <dialog ref="dialog" aria-labelledby="post-moderation-title" @cancel="saving && $event.preventDefault()" @close="decision = undefined">
      <form v-if="decision" class="form-stack" @submit.prevent="moderate">
        <h2 id="post-moderation-title">{{ decision.hide ? 'Ocultar publicación' : decision.item.post.hidden ? 'Restaurar publicación' : 'Cerrar reportes' }}</h2>
        <label>Motivo de la decisión
          <textarea v-model="explanation" rows="3" minlength="3" maxlength="500" :disabled="saving" required></textarea>
        </label>
        <p v-if="decisionError" class="error" role="alert">{{ decisionError }}</p>
        <div class="workshop-actions">
          <button class="button primary" type="submit" :disabled="saving || explanation.trim().length < 3">
            {{ saving ? 'Guardando…' : 'Guardar decisión' }}
          </button>
          <button class="button quiet" type="button" :disabled="saving" @click="close">Cancelar</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.post-moderation { display: grid; gap: .8rem; }
.moderation-item { display: grid; gap: .75rem; padding: 1rem; }
.moderation-title { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .5rem; }
.moderation-details { display: grid; gap: .6rem; }
.moderation-details strong { display: block; }
.moderation-details time { display: block; margin-top: .3rem; font-size: .85rem; }
.post-caption, .moderation-details p { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
