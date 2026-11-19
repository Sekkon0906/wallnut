<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Bell, X } from '@lucide/vue'
import { api, errorText, RequestError } from './client'

const labels = {
  workshop_rescheduled: 'Cambió la agenda de tu taller', workshop_cancelled: 'Se canceló un taller',
  evidence_submitted: 'Hay una evidencia para revisar', evidence_approved: 'Tu evidencia fue aprobada',
  evidence_returned: 'Tu evidencia necesita una corrección', redemption_requested: 'Hay un canje académico para revisar',
  redemption_approved: 'Tu canje académico fue aprobado', redemption_rejected: 'Tu canje académico fue rechazado',
}
interface Cursor { id: string; created_at: string }
interface Entry extends Cursor {
  kind: keyof typeof labels
  title: string
  workshop_id: string | null
  course_id: string | null
  read_at: string | null
}
interface Page { entries: Entry[]; unread_count: number; next_cursor: Cursor | null }
const props = defineProps<{ token: string }>()
const emit = defineEmits<{ expired: []; workshop: [id: string]; course: [id: string] }>()
const modal = ref<HTMLDialogElement>()
const opened = ref(false)
const entries = ref<Entry[]>([])
const nextCursor = ref<Cursor | null>(null)
const unreadCount = ref(0)
const unreadOnly = ref(false)
const loading = ref(false)
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const dates = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota' })
let active = true
let revision = 0
let countRevision = 0
let dialogRevision = 0
let failedAppend = false
let timer: ReturnType<typeof setInterval>

function handleError(error: unknown) {
  if (!active) return
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else problem.value = errorText(error)
}

async function refreshCount() {
  if (document.visibilityState !== 'visible' || opened.value) return
  const current = ++countRevision
  try {
    const value = await api<{ unread_count: number }>('/notifications/unread-count', { token: props.token })
    if (active && current === countRevision) unreadCount.value = value.unread_count
  } catch (error) {
    if (active && current === countRevision && error instanceof RequestError && error.status === 401) emit('expired')
  }
}

async function load(append = false) {
  if (append && (loading.value || !nextCursor.value)) return
  const current = ++revision
  const query = new URLSearchParams({ unread_only: String(unreadOnly.value) })
  if (append && nextCursor.value) {
    query.set('before', nextCursor.value.created_at)
    query.set('before_id', nextCursor.value.id)
  }
  loading.value = true
  problem.value = ''
  failedAppend = append
  try {
    const value = await api<Page>(`/notifications?${query}`, { token: props.token })
    if (!active || current !== revision) return
    entries.value = append ? [...entries.value, ...value.entries] : value.entries
    nextCursor.value = value.next_cursor
    unreadCount.value = value.unread_count
    countRevision++
  } catch (error) {
    if (current === revision) handleError(error)
  } finally {
    if (active && current === revision) loading.value = false
  }
}

async function open() {
  dialogRevision++
  notice.value = ''
  opened.value = true
  await nextTick()
  if (!active) return
  modal.value?.showModal()
  void load()
}

function close() {
  opened.value = false
  dialogRevision++
  modal.value?.close()
}

function filter() {
  entries.value = []
  nextCursor.value = null
  void load()
}

async function mark(entry: Entry, navigate = false) {
  if (busy.value || loading.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  const visit = dialogRevision
  try {
    if (!entry.read_at) {
      const result = await api<{ read_at: string; unread_count: number }>(`/notifications/${entry.id}/read`, {
        token: props.token, method: 'PUT',
      })
      if (!active) return
      countRevision++
      unreadCount.value = result.unread_count
      entries.value = entries.value.map(value => value.id === entry.id ? { ...value, read_at: result.read_at } : value)
      if (unreadOnly.value) entries.value = entries.value.filter(value => !value.read_at)
    }
    if (navigate && opened.value && visit === dialogRevision) {
      close()
      if (entry.workshop_id) emit('workshop', entry.workshop_id)
      else if (entry.course_id) emit('course', entry.course_id)
    } else if (!navigate && visit === dialogRevision) notice.value = 'Aviso marcado como leído.'
  } catch (error) { handleError(error) }
  finally { if (active) busy.value = false }
}

async function markAll() {
  const latest = entries.value[0]
  if (busy.value || loading.value || !latest) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    const result = await api<{ unread_count: number }>('/notifications/read-through', {
      token: props.token, method: 'PUT', data: { id: latest.id, created_at: latest.created_at },
    })
    if (!active) return
    countRevision++
    unreadCount.value = result.unread_count
    await load()
    if (active) notice.value = 'Marcamos los avisos hasta esta consulta. Los que lleguen después seguirán sin leer.'
  } catch (error) { handleError(error) }
  finally { if (active) busy.value = false }
}

onMounted(() => {
  void refreshCount()
  timer = setInterval(() => { void refreshCount() }, 60_000)
  document.addEventListener('visibilitychange', refreshCount)
})
onBeforeUnmount(() => {
  active = false
  clearInterval(timer)
  document.removeEventListener('visibilitychange', refreshCount)
})
</script>

<template>
  <button class="button secondary notification-trigger" type="button" aria-haspopup="dialog"
    :aria-label="unreadCount ? `Avisos, ${unreadCount} sin leer` : 'Avisos'" @click="open">
    <Bell :size="18" aria-hidden="true" /> Avisos <span v-if="unreadCount" class="notification-count" aria-hidden="true">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
  </button>
  <dialog ref="modal" class="notification-dialog" aria-labelledby="notification-title" @close="opened = false" @cancel.prevent="close">
    <div class="dialog-head"><h2 id="notification-title">Tus avisos</h2>
      <button class="icon-button" type="button" aria-label="Cerrar avisos" @click="close"><X :size="22" aria-hidden="true" /></button>
    </div>
    <p class="state-note">Cambios de talleres, evidencias y canjes académicos.</p>
    <div class="notification-controls">
      <label class="notification-unread"><input v-model="unreadOnly" type="checkbox" :disabled="loading || busy" @change="filter" /> Solo sin leer</label>
      <button class="button quiet" type="button" :disabled="loading || busy" @click="load()">Actualizar avisos</button>
      <button v-if="unreadCount && entries.length" class="button quiet" type="button" :disabled="loading || busy" @click="markAll">Marcar todos como leídos</button>
    </div>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="loading" class="state-note" role="status">Consultando avisos…</p>
    <p v-if="!loading && !problem && !entries.length" class="state-note">{{ unreadOnly ? 'Estás al día. No tienes avisos sin leer.' : 'Aquí aparecerán tus próximos avisos.' }}</p>
    <ol class="notification-list">
      <li v-for="entry in entries" :key="entry.id" :class="{ unread: !entry.read_at }">
        <div><span v-if="!entry.read_at" class="badge">Sin leer</span>
          <h3>{{ labels[entry.kind] }}</h3><p>{{ entry.title }}</p>
          <time :datetime="entry.created_at">{{ dates.format(new Date(entry.created_at)) }}</time>
        </div>
        <div class="notification-actions">
          <button class="button secondary" type="button" :disabled="busy || loading" @click="mark(entry, true)">{{ entry.workshop_id ? 'Ver taller' : 'Ver canje' }}</button>
          <button v-if="!entry.read_at" class="button quiet" type="button" :disabled="busy || loading" @click="mark(entry)">Marcar como leído</button>
        </div>
      </li>
    </ol>
    <button v-if="problem" class="button secondary" type="button" :disabled="loading || busy" @click="load(failedAppend)">Reintentar consulta</button>
    <button v-else-if="nextCursor" class="button secondary" type="button" :disabled="loading || busy" @click="load(true)">Ver avisos anteriores</button>
  </dialog>
</template>

<style scoped>
.notification-trigger { position: relative; }
.notification-count { display: inline-grid; place-items: center; min-width: 22px; height: 22px; padding-inline: 5px; border-radius: 20px; color: white; background: var(--blue); font-size: .75rem; }
.notification-dialog { width: min(640px, calc(100% - 24px)); max-height: 85dvh; overflow: auto; }
.notification-controls, .notification-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.notification-unread { display: inline-flex; align-items: center; gap: 7px; font-size: .9rem; }
.notification-unread input { width: 18px; min-height: 18px; accent-color: var(--blue); }
.notification-list { padding: 0; margin: 16px 0; list-style: none; }
.notification-list > li { padding: 15px 10px; border-block-start: 1px solid var(--line); }
.notification-list > li.unread { border-inline-start: 3px solid var(--blue); background: #f4f8ff; }
.notification-list h3 { margin: 6px 0; font-size: 1rem; overflow-wrap: anywhere; }
.notification-list p { margin: 5px 0; overflow-wrap: anywhere; }
.notification-list time { font-size: .8rem; color: var(--muted); }
.notification-actions { margin-top: 10px; }
</style>
