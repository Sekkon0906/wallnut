<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, errorText, RequestError } from './client'

type Partner = { id: string; name: string }
type Invitation = { id: string; name: string; outgoing: boolean }
type Pairing = {
  open: boolean
  enrolled: boolean
  pair: Invitation | null
  invitations: Invitation[]
  available: Partner[]
}

const props = defineProps<{ token: string; eventId: string; locked: boolean }>()
const emit = defineEmits<{ expired: []; changed: [] }>()
const endpoint = `/campus-events/${props.eventId}/tournament`
const pairing = ref<Pairing>()
const selection = ref('')
const busy = ref(false)
const problem = ref('')
const notice = ref('')
let request: { id: string; student_id: string } | undefined

async function load() {
  pairing.value = await api<Pairing>(`${endpoint}/pairing`, { token: props.token })
}

async function perform(action: () => Promise<void>, message = '') {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    await action()
    notice.value = message
    if (message) emit('changed')
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

function invite() {
  if (!selection.value) return
  void perform(async () => {
    if (request?.student_id !== selection.value) {
      request = { id: crypto.randomUUID(), student_id: selection.value }
    }
    pairing.value = await api<Pairing>(`${endpoint}/pair-invitations`, {
      token: props.token, method: 'POST', data: request,
    })
    request = undefined
    selection.value = ''
  }, 'Invitación enviada.')
}

function update(id: string, accept: boolean, message: string) {
  void perform(async () => {
    pairing.value = await api<Pairing>(`${endpoint}/pair-invitations/${id}${accept ? '/accept' : ''}`, {
      token: props.token, method: accept ? 'PUT' : 'DELETE',
    })
    request = undefined
    selection.value = ''
  }, message)
}

onMounted(() => perform(load))
</script>

<template>
  <section class="tile form-stack tournament-pairing" aria-labelledby="pairing-heading">
    <div class="pairing-top">
      <h3 id="pairing-heading">Mi pareja</h3>
      <button type="button" class="button quiet" :disabled="busy || locked" @click="perform(load)">Actualizar pareja</button>
    </div>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="busy && !pairing" role="status">Consultando inscripciones…</p>
    <template v-if="pairing">
      <div v-if="pairing.pair" class="workshop-actions">
        <p>Pareja confirmada con <strong>{{ pairing.pair.name }}</strong>.</p>
        <button v-if="pairing.open" type="button" class="button secondary" :disabled="busy || locked"
          @click="update(pairing.pair.id, false, 'Pareja disuelta. Ambos conservan su cupo.')">Disolver pareja</button>
      </div>
      <p v-else-if="!pairing.open">El registro de parejas está cerrado.</p>
      <p v-else-if="!pairing.enrolled">Inscríbete en el evento para invitar o aceptar a una pareja.</p>
      <template v-else>
        <ul v-if="pairing.invitations.length" class="pairing-invitations">
          <li v-for="item in pairing.invitations" :key="item.id" class="pairing-invitation">
            <span>{{ item.outgoing ? 'Invitaste a' : 'Te invitó' }} <strong>{{ item.name }}</strong></span>
            <div class="workshop-actions">
              <button v-if="!item.outgoing" type="button" class="button primary" :disabled="busy || locked"
                @click="update(item.id, true, 'Pareja confirmada.')">Aceptar</button>
              <button type="button" class="button secondary" :disabled="busy || locked"
                @click="update(item.id, false, item.outgoing ? 'Invitación cancelada.' : 'Invitación rechazada.')">
                {{ item.outgoing ? 'Cancelar invitación' : 'Rechazar' }}
              </button>
            </div>
          </li>
        </ul>
        <form v-if="!pairing.invitations.some(item => item.outgoing) && pairing.available.length"
          class="form-stack" @submit.prevent="invite">
          <label>Compañero inscrito
            <select v-model="selection" required :disabled="busy || locked">
              <option value="" disabled>Elige a tu pareja</option>
              <option v-for="partner in pairing.available" :key="partner.id" :value="partner.id">{{ partner.name }}</option>
            </select>
          </label>
          <button class="button primary" type="submit" :disabled="!selection || busy || locked">Enviar invitación</button>
        </form>
        <p v-if="!pairing.available.length && !pairing.invitations.length">
          Todavía no hay otros estudiantes inscritos con quienes puedas formar pareja.
        </p>
      </template>
    </template>
  </section>
</template>

<style scoped>
.tournament-pairing { padding: 1rem; margin: 1rem 0; }
.pairing-top, .pairing-invitation { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem 1rem; justify-content: space-between; }
.pairing-invitations { list-style: none; padding: 0; margin: 0; display: grid; gap: .5rem; }
.pairing-invitation { border-top: 1px solid var(--line); padding-top: .5rem; overflow-wrap: anywhere; }
.tournament-pairing form > button { justify-self: start; }
</style>
