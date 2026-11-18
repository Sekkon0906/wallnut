<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CalendarDays, MapPin, Megaphone, MessageSquare, RefreshCw } from '@lucide/vue'
import { api, errorText, RequestError } from './client'
import { postDate } from './campusPosts'
import { eventCategories } from './campusEvents'
import type { FeedEntry, FeedPage, FeedTarget } from './communityFeed'
import CampusPostPhoto from './CampusPostPhoto.vue'
import CampusProfileDialog from './CampusProfileDialog.vue'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ expired: []; open: [entry: FeedTarget] }>()
const items = ref<FeedEntry[]>([])
const origin = ref('all')
const loading = ref(false)
const problem = ref('')
const nextCursor = ref<string | null>(null)
const openedProfile = ref('')
const icons = { post: MessageSquare, event: CalendarDays, call: Megaphone }
const labels = { post: 'Publicación', event: 'Evento', call: 'Convocatoria' }
let revision = 0

async function load(append = false) {
  if (append && (loading.value || !nextCursor.value)) return
  const requestRevision = append ? revision : ++revision
  const parameters = new URLSearchParams({ origin: origin.value })
  if (append && nextCursor.value) parameters.set('cursor', nextCursor.value)
  if (!append) {
    items.value = []
    nextCursor.value = null
  }
  loading.value = true
  problem.value = ''
  try {
    const page = await api<FeedPage>(`/community-feed?${parameters}`, { token: props.token })
    if (requestRevision !== revision) return
    items.value = append ? [...items.value, ...page.items] : page.items
    nextCursor.value = page.next_cursor
  } catch (error) {
    if (requestRevision !== revision) return
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    if (requestRevision === revision) loading.value = false
  }
}

watch(origin, () => load())
onMounted(() => load())
onBeforeUnmount(() => { revision++ })
</script>

<template>
  <section class="community-timeline" aria-labelledby="timeline-title">
    <div class="section-heading">
      <h2 id="timeline-title">Lo último del campus</h2>
      <button class="button secondary" type="button" :disabled="loading" @click="load()">
        <RefreshCw :size="17" aria-hidden="true" /> Actualizar
      </button>
    </div>
    <label class="timeline-origin">Procedencia
      <select v-model="origin">
        <option value="all">Toda la comunidad</option>
        <option value="university">Universidad</option>
        <option value="students">Estudiantes</option>
      </select>
    </label>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="loading" role="status">Cargando Comunidad…</p>
    <p v-else-if="!problem && !items.length" class="tile state-note">Todavía no hay contenido de esta procedencia.</p>
    <div class="timeline-entries">
      <article v-for="entry in items" :key="`${entry.kind}-${entry.id}`" class="tile timeline-entry">
        <header class="timeline-byline">
          <div class="timeline-icon"><component :is="icons[entry.kind]" :size="22" aria-hidden="true" /></div>
          <div>
            <span class="timeline-kind">{{ labels[entry.kind] }} · {{ entry.institutional ? 'Universidad' : 'Estudiantes' }}</span>
            <time :datetime="entry.published_at">{{ postDate.format(new Date(entry.published_at)) }}</time>
          </div>
        </header>

        <template v-if="entry.kind === 'post'">
          <button v-if="entry.content.author_profile_visible" class="timeline-profile" type="button"
            :aria-label="`Ver perfil de ${entry.content.author}`" @click="openedProfile = entry.content.author_id">{{ entry.content.author }}</button>
          <h3 v-else>{{ entry.content.author }}</h3>
          <p v-if="entry.content.hidden" class="state-note">Oculta por moderación</p>
          <p v-if="entry.content.body" class="timeline-body">{{ entry.content.body }}</p>
          <CampusPostPhoto v-if="entry.content.has_photo" :token="token" :post-id="entry.id" :version="entry.content.updated_at"
            @expired="emit('expired')" />
          <button class="button quiet" type="button" @click="emit('open', entry)">Ver publicación</button>
        </template>

        <template v-else-if="entry.kind === 'event'">
          <div class="call-meta">
            <span>{{ eventCategories[entry.content.category] }}</span>
            <span v-if="entry.content.cancelled" class="badge">Cancelado</span>
            <span v-else-if="!entry.content.upcoming" class="badge">Ya inició</span>
            <span v-if="entry.content.enrolled" class="badge">Inscripción confirmada</span>
          </div>
          <h3>{{ entry.content.title }}</h3>
          <p class="timeline-body">{{ entry.content.description }}</p>
          <p class="timeline-location"><MapPin :size="16" aria-hidden="true" />{{ entry.content.location }} · {{ postDate.format(new Date(entry.content.starts_at)) }}</p>
          <p>{{ entry.content.organizer }} · {{ entry.content.attendees }} de {{ entry.content.capacity }} cupos ocupados</p>
          <button class="button secondary" type="button" @click="emit('open', entry)">Ver evento</button>
        </template>

        <template v-else>
          <div class="call-meta">
            <span>{{ entry.content.course }}</span>
            <span class="badge">{{ entry.content.open ? 'Busca tallerista' : 'Tallerista confirmado' }}</span>
          </div>
          <h3>{{ entry.content.title }}</h3>
          <p class="timeline-body">{{ entry.content.description }}</p>
          <p>{{ entry.content.faculty }}</p>
          <button class="button secondary" type="button" @click="emit('open', entry)">Ver convocatoria</button>
        </template>
      </article>
    </div>
    <button v-if="nextCursor || problem" class="button secondary show-more" type="button" :disabled="loading"
      @click="load(!!nextCursor)">{{ problem ? 'Reintentar' : 'Ver más contenido' }}</button>
    <CampusProfileDialog v-if="openedProfile" :token="token" :student-id="openedProfile"
      @close="openedProfile = ''" @expired="emit('expired')" />
  </section>
</template>

<style scoped>
.community-timeline, .timeline-entries { display: grid; gap: 1rem; }
.timeline-origin { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem; color: var(--muted); }
.timeline-origin select { min-height: 44px; border: 1px solid var(--line); border-radius: 10px; background: white; padding: .4rem .65rem; color: var(--ink); }
.timeline-entry { display: grid; justify-items: start; gap: .7rem; min-width: 0; overflow-wrap: anywhere; }
.timeline-byline { display: flex; align-items: center; gap: .7rem; }
.timeline-icon { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 12px; background: var(--light); color: var(--blue); flex-shrink: 0; }
.timeline-byline time { display: block; color: var(--muted); font-size: .8rem; }
.timeline-kind { font-size: .87rem; font-weight: 650; }
.timeline-body { white-space: pre-wrap; }
.timeline-location { display: flex; align-items: baseline; flex-wrap: wrap; gap: .3rem; font-size: .9rem; }
.timeline-profile { color: var(--blue); background: none; border: 0; padding: .25rem 0; font-weight: 700; text-decoration: underline; text-underline-offset: .15em; }
.timeline-entry :deep(.post-photo) { width: 100%; }
</style>
