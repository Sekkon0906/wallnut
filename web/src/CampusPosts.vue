<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Plus } from '@lucide/vue'
import { api, errorText, RequestError, type Role } from './client'
import { postDate, postPageSize, type CampusPost } from './campusPosts'
import CampusPostModeration from './CampusPostModeration.vue'
import CampusPostPhoto from './CampusPostPhoto.vue'
import CampusProfileDialog from './CampusProfileDialog.vue'

type Action = 'create' | 'edit' | 'delete' | 'report'
const props = defineProps<{ token: string; role: Role; postId?: string }>()
const emit = defineEmits<{ expired: [] }>()
const actionTitles: Record<Action, string> = {
  create: 'Nueva publicación',
  edit: 'Editar publicación',
  delete: 'Eliminar publicación',
  report: 'Reportar publicación',
}
const posts = ref<CampusPost[]>([])
const showingReports = ref(false)
const openedProfile = ref('')
const loaded = ref(false)
const loading = ref(false)
const saving = ref(false)
const more = ref(false)
const notice = ref('')
const problem = ref('')
const dialogProblem = ref('')
const action = ref<Action>()
const selected = ref<CampusPost>()
const dialog = ref<HTMLDialogElement>()
const caption = ref('')
const photo = ref<File>()
const photoInput = ref<HTMLInputElement>()
const previewUrl = ref('')
const removePhoto = ref(false)
const reason = ref('')
let offset = 0
let draftId = ''
let active = true
const validDraft = computed(() => !!caption.value.trim() || !!photo.value
  || (!!selected.value?.has_photo && !removePhoto.value))

function handleError(error: unknown, target: typeof problem) {
  if (!active) return
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else target.value = errorText(error)
}

async function load(append = false) {
  if (loading.value) return
  loading.value = true
  problem.value = ''
  try {
    if (props.postId) {
      posts.value = [await api<CampusPost>(`/posts/${props.postId}`, { token: props.token })]
      more.value = false
      loaded.value = true
      return
    }
    const from = append ? offset : 0
    const rows = await api<CampusPost[]>(`/posts?offset=${from}`, { token: props.token })
    const page = rows.slice(0, postPageSize)
    if (append) {
      const known = new Set(posts.value.map(post => post.id))
      posts.value = [...posts.value, ...page.filter(post => !known.has(post.id))]
    } else posts.value = page
    offset = from + page.length
    more.value = rows.length > postPageSize
    loaded.value = true
  } catch (error) {
    handleError(error, problem)
  } finally {
    loading.value = false
  }
}

function toggleReports() {
  showingReports.value = !showingReports.value
  if (!showingReports.value) void load()
}

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  photo.value = undefined
}

function forgetFile() {
  clearPreview()
  if (photoInput.value) photoInput.value.value = ''
}

function selectPhoto(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  clearPreview()
  dialogProblem.value = ''
  if (!file) return
  if (file.size > 8 * 1024 * 1024) {
    input.value = ''
    dialogProblem.value = 'La foto debe pesar 8 MB o menos.'
    return
  }
  photo.value = file
  previewUrl.value = URL.createObjectURL(file)
  removePhoto.value = false
}

async function open(mode: Action, post?: CampusPost) {
  action.value = mode
  selected.value = post
  caption.value = mode === 'edit' ? post?.body ?? '' : ''
  reason.value = ''
  removePhoto.value = false
  forgetFile()
  draftId = mode === 'create' ? crypto.randomUUID() : ''
  dialogProblem.value = ''
  await nextTick()
  dialog.value?.showModal()
}

function close() {
  if (!saving.value) dialog.value?.close()
}

function resetDialog() {
  action.value = undefined
  selected.value = undefined
  clearPreview()
}

async function submit() {
  if (saving.value || !action.value) return
  const mode = action.value
  const post = selected.value
  if ((mode === 'create' || mode === 'edit') && !validDraft.value) return
  if (mode === 'report' && reason.value.trim().length < 3) return
  saving.value = true
  dialogProblem.value = ''
  notice.value = ''
  try {
    if (mode === 'create' || (mode === 'edit' && post)) {
      const data = new FormData()
      data.set('body', caption.value.trim())
      if (photo.value) data.set('photo', photo.value)
      if (removePhoto.value) data.set('remove_photo', 'true')
      if (mode === 'create') data.set('id', draftId)
      const result = await api<CampusPost>(post ? `/posts/${post.id}` : '/posts', {
        token: props.token, method: post ? 'PUT' : 'POST', data,
      })
      if (post) posts.value = posts.value.map(item => item.id === result.id ? result : item)
      notice.value = post ? 'Cambios guardados.' : 'Publicación compartida.'
    } else if (post && mode === 'delete') {
      await api(`/posts/${post.id}`, { token: props.token, method: 'DELETE' })
      posts.value = posts.value.filter(item => item.id !== post.id)
      notice.value = 'Publicación eliminada.'
    } else if (post && mode === 'report') {
      await api(`/posts/${post.id}/report`, { token: props.token, method: 'POST', data: { reason: reason.value.trim() } })
      posts.value = posts.value.map(item => item.id === post.id ? { ...item, reported: true } : item)
      notice.value = 'Reporte enviado a administración.'
    }
    dialog.value?.close()
    if ((mode === 'create' || mode === 'delete') && !props.postId) await load()
  } catch (error) {
    handleError(error, dialogProblem)
  } finally {
    saving.value = false
  }
}

onMounted(() => load())
onBeforeUnmount(() => {
  active = false
  clearPreview()
})
</script>

<template>
  <section class="campus-posts" aria-labelledby="campus-posts-title">
    <div class="section-heading">
      <h2 id="campus-posts-title">{{ showingReports ? 'Moderación de publicaciones' : 'Publicaciones' }}</h2>
      <div class="workshop-actions">
        <button v-if="role === 'admin' && !postId" class="button secondary" type="button" @click="toggleReports">
          {{ showingReports ? 'Ver publicaciones' : 'Revisar reportes' }}
        </button>
        <button v-if="role !== 'staff' && !showingReports && !postId" class="button primary" type="button"
          :disabled="loading || saving" @click="open('create')">
          <Plus :size="18" aria-hidden="true" /> Crear publicación
        </button>
      </div>
    </div>
    <CampusPostModeration v-if="showingReports" :token="token" @expired="emit('expired')" />
    <template v-else>
      <p v-if="notice" class="success" role="status">{{ notice }}</p>
      <p v-if="problem" class="error" role="alert">{{ problem }}</p>
      <button v-if="problem" class="button quiet" type="button" :disabled="loading" @click="load()">Actualizar publicaciones</button>
      <p v-if="loading" class="state-note" role="status">Cargando publicaciones…</p>
      <p v-else-if="loaded && !posts.length" class="tile state-note">Aún no hay publicaciones.</p>
      <div class="campus-post-list">
        <article v-for="post in posts" :key="post.id" class="tile campus-post">
          <header class="post-byline">
            <div>
              <button v-if="post.author_profile_visible" class="post-author-link" type="button"
                :aria-label="`Ver perfil de ${post.author}`" @click="openedProfile = post.author_id">{{ post.author }}</button>
              <h3 v-else>{{ post.author }}</h3>
              <time :datetime="post.created_at">{{ postDate.format(new Date(post.created_at)) }}</time>
              <span v-if="post.updated_at" class="post-edited">· Editada</span>
            </div>
            <span v-if="post.hidden" class="badge">Oculta por moderación</span>
          </header>
          <p v-if="post.body" class="post-caption">{{ post.body }}</p>
          <CampusPostPhoto v-if="post.has_photo" :token="token" :post-id="post.id" :version="post.updated_at"
            @expired="emit('expired')" />
          <p v-if="post.hidden && post.moderation_reason" class="post-caption">Motivo: {{ post.moderation_reason }}</p>
          <div class="workshop-actions">
            <button v-if="post.mine" class="button quiet" type="button" :disabled="loading || saving" @click="open('edit', post)">Editar</button>
            <button v-if="post.mine" class="button quiet post-delete" type="button" :disabled="loading || saving"
              @click="open('delete', post)">Eliminar</button>
            <button v-if="!post.mine && !post.reported && !post.hidden" class="button quiet" type="button"
              :disabled="loading || saving" @click="open('report', post)">Reportar</button>
            <span v-if="!post.mine && post.reported" class="post-reported">Reporte enviado</span>
          </div>
        </article>
      </div>
      <button v-if="more" class="button secondary posts-more" type="button" :disabled="loading" @click="load(true)">Cargar más publicaciones</button>
    </template>

    <dialog ref="dialog" aria-labelledby="campus-post-dialog-title" @cancel="saving && $event.preventDefault()" @close="resetDialog">
      <form v-if="action" class="form-stack" @submit.prevent="submit">
        <h2 id="campus-post-dialog-title">{{ actionTitles[action] }}</h2>
        <template v-if="action === 'create' || action === 'edit'">
          <label>Texto
            <textarea v-model="caption" rows="4" maxlength="1200" :disabled="saving" placeholder="Comparte algo con la comunidad"></textarea>
          </label>
          <label>{{ selected?.has_photo ? 'Reemplazar foto' : 'Adjuntar foto' }}
            <input ref="photoInput" type="file" accept="image/jpeg,image/png,image/webp" :disabled="saving" @change="selectPhoto" />
          </label>
          <img v-if="previewUrl" :src="previewUrl" alt="Vista previa de la foto" class="post-upload-preview" />
          <button v-if="photo" class="button quiet post-clear-photo" type="button" :disabled="saving" @click="forgetFile">Quitar foto seleccionada</button>
          <label v-else-if="selected?.has_photo" class="check-label">
            <input v-model="removePhoto" type="checkbox" :disabled="saving" /> Quitar foto actual
          </label>
          <p class="state-note">Puedes publicar texto, una foto o ambos. La foto puede pesar hasta 8 MB.</p>
        </template>
        <template v-else-if="action === 'report'">
          <label>Motivo del reporte
            <textarea v-model="reason" rows="3" minlength="3" maxlength="500" :disabled="saving" required></textarea>
          </label>
        </template>
        <p v-else>La publicación dejará de aparecer en Comunidad.</p>
        <p v-if="dialogProblem" class="error" role="alert">{{ dialogProblem }}</p>
        <div class="workshop-actions">
          <button class="button primary" type="submit"
            :disabled="saving || ((action === 'create' || action === 'edit') && !validDraft) || (action === 'report' && reason.trim().length < 3)">
            {{ saving ? 'Guardando…' : action === 'create' ? 'Publicar' : action === 'edit' ? 'Guardar cambios' : action === 'report' ? 'Enviar reporte' : 'Eliminar publicación' }}
          </button>
          <button class="button quiet" type="button" :disabled="saving" @click="close">Cancelar</button>
        </div>
      </form>
    </dialog>
    <CampusProfileDialog v-if="openedProfile" :token="token" :student-id="openedProfile"
      @close="openedProfile = ''" @expired="emit('expired')" />
  </section>
</template>

<style scoped>
.campus-posts { min-width: 0; margin-bottom: 1.5rem; }
.campus-post-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .85rem; align-items: start; }
.campus-post { display: grid; gap: .75rem; padding: 1rem; min-width: 0; }
.post-byline { display: flex; align-items: start; justify-content: space-between; gap: .55rem; flex-wrap: wrap; }
.post-byline h3, .post-author-link { font-size: 1rem; font-weight: 760; overflow-wrap: anywhere; }
.post-author-link { display: block; border: 0; padding: 0; background: none; color: var(--blue); text-align: left; text-decoration: underline; text-underline-offset: .15em; }
.post-byline time, .post-edited, .post-reported { font-size: .85rem; color: var(--muted); }
.post-edited { margin-left: .3rem; }
.post-caption { white-space: pre-wrap; overflow-wrap: anywhere; }
.post-delete { color: #972643; }
.post-upload-preview { display: block; max-width: 100%; max-height: 18rem; border-radius: .75rem; object-fit: contain; }
.post-clear-photo { justify-self: start; }
.posts-more { margin-top: .9rem; }
@media (max-width: 720px) { .campus-post-list { grid-template-columns: minmax(0, 1fr); } }
</style>
