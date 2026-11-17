<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowUpRight, Send, X } from '@lucide/vue'
import { api, errorText, RequestError } from './client'

type Destination = 'community' | 'events' | 'posts' | 'calls' | 'agenda' | 'groups' | 'wallet' | 'ardy' | 'ranking'
type Topic = { id: string; title: string }
type Answer = { answer: string; action: Destination | null }
type Message = { text: string; sender: 'user' | 'ardi'; action?: Destination | null }
const props = defineProps<{ token: string }>()
const emit = defineEmits<{ expired: []; navigate: [destination: Destination]; close: [] }>()
const actionLabels: Record<Destination, string> = {
  community: 'Abrir Comunidad',
  events: 'Ver Eventos',
  posts: 'Ver Publicaciones',
  calls: 'Ver Convocatorias',
  agenda: 'Abrir Agenda',
  groups: 'Abrir gestión académica',
  wallet: 'Abrir Billetera',
  ardy: 'Abrir Mi Ardy',
  ranking: 'Abrir Ranking',
}
const dialog = ref<HTMLDialogElement>()
const conversation = ref<HTMLElement>()
const messages = ref<Message[]>([])
const topics = ref<Topic[]>([])
const question = ref('')
const loadingTopics = ref(false)
const asking = ref(false)
const topicsError = ref('')
const questionError = ref('')
let active = true

function handleError(error: unknown, target: typeof questionError) {
  if (!active) return
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else target.value = errorText(error)
}

async function loadTopics() {
  if (loadingTopics.value) return
  loadingTopics.value = true
  topicsError.value = ''
  try {
    const data = await api<{ topics: Topic[] }>('/ardi-help', { token: props.token })
    topics.value = data.topics
  } catch (error) {
    handleError(error, topicsError)
  } finally {
    loadingTopics.value = false
  }
}

async function showLatest() {
  await nextTick()
  const area = conversation.value
  if (area) area.scrollTop = area.scrollHeight
}

async function ask(topic?: Topic) {
  const text = topic?.title ?? question.value.trim()
  if (asking.value || !text || text.length > 300) return
  asking.value = true
  questionError.value = ''
  if (!topic) question.value = ''
  messages.value = [...messages.value.slice(-38), { sender: 'user', text }]
  void showLatest()
  try {
    const { answer, action } = await api<Answer>('/ardi-help', {
      token: props.token,
      method: 'POST',
      data: { question: text, ...(topic && { topic: topic.id }) },
    })
    if (active) messages.value.push({ sender: 'ardi', text: answer, action })
  } catch (error) {
    messages.value.pop()
    if (!topic && !question.value) question.value = text
    handleError(error, questionError)
  } finally {
    asking.value = false
    void showLatest()
  }
}

onMounted(() => {
  dialog.value?.showModal()
  void loadTopics()
})
onBeforeUnmount(() => { active = false })
</script>

<template>
  <dialog ref="dialog" class="ardi-help" aria-labelledby="ardi-help-title" @close="emit('close')">
    <div class="ardi-help-shell">
      <header class="ardi-help-header">
        <div class="ardi-help-brand">
          <img src="/ardy.webp" alt="" width="44" height="44" />
          <h2 id="ardi-help-title">Ayuda de Ardi</h2>
        </div>
        <button class="icon-button" type="button" aria-label="Cerrar ayuda" autofocus @click="dialog?.close()">
          <X :size="20" aria-hidden="true" />
        </button>
      </header>

      <div ref="conversation" class="ardi-help-scroll">
        <section class="ardi-help-topics" aria-labelledby="ardi-topics-title">
          <h3 id="ardi-topics-title">Temas frecuentes</h3>
          <p v-if="loadingTopics" class="state-note" role="status">Cargando temas…</p>
          <p v-if="topicsError" class="error" role="alert">{{ topicsError }}</p>
          <button v-if="topicsError" class="button quiet" type="button" :disabled="loadingTopics" @click="loadTopics">
            Volver a cargar temas
          </button>
          <div v-if="topics.length" class="ardi-topic-buttons">
            <button v-for="topic in topics" :key="topic.id" class="filter" type="button" :disabled="asking" @click="ask(topic)">
              {{ topic.title }}
            </button>
          </div>
        </section>

        <div class="ardi-help-messages" role="log" aria-label="Conversación con Ardi" aria-live="polite" aria-relevant="additions">
          <article v-for="(message, index) in messages" :key="index" class="ardi-message" :data-sender="message.sender">
            <span class="ardi-message-author">{{ message.sender === 'ardi' ? 'Ardi' : 'Tú' }}</span>
            <p>{{ message.text }}</p>
            <button v-if="message.action" type="button" class="button secondary ardi-message-link"
              @click="emit('navigate', message.action)">
              {{ actionLabels[message.action] }} <ArrowUpRight :size="16" aria-hidden="true" />
            </button>
          </article>
        </div>
        <p v-if="asking" class="ardi-help-status" role="status">Ardi está buscando una respuesta…</p>
      </div>

      <form class="form-stack ardi-help-form" @submit.prevent="ask()">
        <p v-if="questionError" class="error" role="alert">{{ questionError }}</p>
        <label for="ardi-help-question">Tu pregunta</label>
        <div class="ardi-help-compose">
          <textarea id="ardi-help-question" v-model="question" rows="2" maxlength="300"
            placeholder="¿Cómo me inscribo a un taller?"></textarea>
          <button class="button primary" type="submit" :disabled="asking || !question.trim()">
            <Send :size="17" aria-hidden="true" /> Enviar
          </button>
        </div>
      </form>
    </div>
  </dialog>
</template>

<style scoped>
.ardi-help {
  width: min(calc(100% - 1rem), 37rem);
  height: min(42rem, calc(100dvh - 1rem));
  max-height: none;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 1.5rem 4rem #10264838;
}
.ardi-help-shell { height: 100%; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; }
.ardi-help-header, .ardi-help-brand { display: flex; align-items: center; gap: .7rem; }
.ardi-help-header { justify-content: space-between; padding: .75rem 1rem; border-bottom: 1px solid var(--line); }
.ardi-help-brand img { flex: none; border-radius: 13px; background: var(--light); object-fit: contain; }
.ardi-help-brand h2 { font-size: 1.2rem; }
.ardi-help-scroll { overflow: auto; overscroll-behavior: contain; padding: 1rem; background: #f8faff; }
.ardi-help-topics h3 { font-size: .95rem; margin: 0 0 .5rem; }
.ardi-topic-buttons { display: flex; align-items: center; flex-wrap: wrap; gap: .45rem; }
.ardi-topic-buttons .filter { font-size: .86rem; min-height: 40px; background: white; }
.ardi-topic-buttons .filter:hover:enabled { background: var(--light); }
.ardi-help-messages { display: grid; grid-template-columns: minmax(0, 1fr); gap: .75rem; margin-top: .85rem; }
.ardi-message {
  display: grid;
  gap: .35rem;
  max-width: min(90%, 30rem);
  justify-self: start;
  padding: .75rem .9rem;
  border-radius: 0 14px 14px;
  background: white;
  border: 1px solid var(--line);
  overflow-wrap: anywhere;
}
.ardi-message[data-sender='user'] { justify-self: end; background: var(--light); border-radius: 14px 0 14px 14px; }
.ardi-message-author { font-size: .8rem; font-weight: 750; color: var(--blue); }
.ardi-message p { white-space: pre-wrap; }
.ardi-message-link { justify-self: start; margin-top: .15rem; }
.ardi-help-status { margin-top: .75rem; font-size: .9rem; }
.ardi-help-form { padding: .7rem 1rem max(.7rem, env(safe-area-inset-bottom)); gap: .4rem; border-top: 1px solid var(--line); }
.ardi-help-form .error { margin: 0; }
.ardi-help-compose { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: .6rem; }
.ardi-help-compose textarea { max-height: 10dvh; min-height: 3.15rem; resize: none; }
@media (max-width: 480px) {
  .ardi-help-header, .ardi-help-form { padding-inline: .75rem; }
  .ardi-help-scroll { padding: .75rem; }
  .ardi-message { max-width: 96%; }
}
</style>
