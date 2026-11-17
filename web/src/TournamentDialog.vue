<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { Trophy, X } from '@lucide/vue'
import { api, errorText, RequestError, type Role } from './client'
import TournamentPairing from './TournamentPairing.vue'

type Participant = { id: string; name: string }
type Match = {
  number: number
  status: 'waiting' | 'ready' | 'bye' | 'completed'
  first: Participant | null
  second: Participant | null
  winner_id: string | null
  score?: string | null
}
type Tournament = {
  event_id: string
  title: string
  state: 'registration' | 'in_progress' | 'completed' | 'cancelled'
  can_manage: boolean
  can_generate: boolean
  participant_count: number
  entrant_count: number
  unpaired_count: number
  tournament_format: 'individual' | 'doubles'
  champion: Participant | null
  rounds: { number: number; matches: Match[] }[]
}

const props = defineProps<{ eventId: string; token: string; role: Role }>()
const emit = defineEmits<{ expired: []; close: []; generated: [] }>()
const dialog = ref<HTMLDialogElement>()
const winnerInput = ref<HTMLSelectElement>()
const tournament = ref<Tournament>()
const editing = ref<{ round: number; match: Match }>()
const winner = ref('')
const score = ref('')
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const confirmBracket = ref(false)
const endpoint = `/campus-events/${props.eventId}/tournament`
const matchStates = { waiting: 'Pendiente', ready: 'Por jugar', bye: 'Pase directo', completed: 'Finalizado' }

function roundTitle(number: number, total: number) {
  const finalRounds = ['Final', 'Semifinales', 'Cuartos de final']
  return finalRounds[total - number] ?? `Ronda ${number}`
}

async function perform(action: () => Promise<void>) {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    await action()
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

function load() {
  return perform(async () => {
    tournament.value = await api<Tournament>(endpoint, { token: props.token })
  })
}

function generate() {
  return perform(async () => {
    tournament.value = await api<Tournament>(`${endpoint}/bracket`, { token: props.token, method: 'POST' })
    confirmBracket.value = false
    notice.value = 'Cuadro generado. Las inscripciones quedaron cerradas.'
    emit('generated')
  })
}

async function selectMatch(round: number, match: Match) {
  editing.value = { round, match }
  winner.value = ''
  score.value = ''
  problem.value = ''
  notice.value = ''
  await nextTick()
  winnerInput.value?.focus()
}

function record() {
  const selection = editing.value
  if (!selection || !winner.value) return
  return perform(async () => {
    tournament.value = await api<Tournament>(
      `${endpoint}/matches/${selection.round}/${selection.match.number}`,
      { token: props.token, method: 'PUT', data: { winner_id: winner.value, score: score.value.trim() || null } },
    )
    editing.value = undefined
    notice.value = 'Resultado guardado.'
  })
}

onMounted(() => {
  dialog.value?.showModal()
  void load()
})
</script>

<template>
  <dialog ref="dialog" class="tournament-dialog" aria-labelledby="tournament-heading"
    @close="emit('close')" @cancel="busy && $event.preventDefault()">
    <header class="tournament-header">
      <h2 id="tournament-heading">{{ tournament?.title ?? 'Torneo' }}</h2>
      <button class="button quiet" type="button" aria-label="Cerrar cuadro del torneo" :disabled="busy" @click="dialog?.close()">
        <X :size="21" aria-hidden="true" />
      </button>
    </header>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="busy && !tournament" role="status">Cargando torneo…</p>
    <button v-if="problem && !tournament" class="button secondary" type="button" @click="load">Reintentar</button>
    <template v-if="tournament">
      <p v-if="tournament.state === 'cancelled'" class="state-note">Este torneo fue cancelado.</p>
      <p v-if="tournament.champion" class="tournament-champion">
        <Trophy :size="22" aria-hidden="true" />
        {{ tournament.tournament_format === 'doubles' ? 'Pareja campeona' : 'Campeón' }} · <strong>{{ tournament.champion.name }}</strong>
      </p>
      <div v-if="!tournament.rounds.length && tournament.state !== 'cancelled'" class="tournament-registration">
        <p v-if="tournament.tournament_format === 'doubles'">
          {{ tournament.entrant_count }} parejas confirmadas y {{ tournament.unpaired_count }} estudiantes sin pareja.
          El cuadro requiere al menos dos parejas.
        </p>
        <p v-else>Hay {{ tournament.participant_count }} participantes inscritos. El cuadro requiere al menos dos.</p>
        <div v-if="!confirmBracket" class="workshop-actions">
          <button v-if="tournament.can_generate" class="button primary" type="button" :disabled="busy" @click="confirmBracket = true">
            Generar cuadro
          </button>
          <button class="button quiet" type="button" :disabled="busy" @click="load">Actualizar torneo</button>
        </div>
        <template v-else-if="confirmBracket">
          <p>Se cerrarán las inscripciones y el cuadro quedará listo para registrar resultados.</p>
          <p v-if="tournament.unpaired_count">El cuadro incluirá solo parejas confirmadas. Hay {{ tournament.unpaired_count }} estudiantes sin pareja.</p>
          <div class="workshop-actions">
            <button class="button primary" type="button" :disabled="busy" @click="generate">Confirmar cuadro</button>
            <button class="button quiet" type="button" :disabled="busy" @click="confirmBracket = false">Volver</button>
          </div>
        </template>
      </div>
      <TournamentPairing v-if="tournament.tournament_format === 'doubles' && tournament.state === 'registration' && role === 'student'"
        :token="token" :event-id="eventId" :locked="busy || confirmBracket" @expired="emit('expired')" @changed="load" />
      <form v-if="editing" class="tile form-stack tournament-result" @submit.prevent="record">
        <h3>{{ roundTitle(editing.round, tournament.rounds.length) }} · Partido {{ editing.match.number }}</h3>
        <label>{{ tournament.tournament_format === 'doubles' ? 'Pareja ganadora' : 'Ganador' }}
          <select ref="winnerInput" v-model="winner" required :disabled="busy">
            <option value="" disabled>Selecciona un participante</option>
            <option v-if="editing.match.first" :value="editing.match.first.id">{{ editing.match.first.name }}</option>
            <option v-if="editing.match.second" :value="editing.match.second.id">{{ editing.match.second.name }}</option>
          </select>
        </label>
        <label>Marcador (opcional)
          <input v-model="score" maxlength="80" placeholder="Ej. 6–3, 6–4" :disabled="busy" />
        </label>
        <div class="workshop-actions">
          <button class="button primary" type="submit" :disabled="busy || !winner">Guardar resultado</button>
          <button class="button quiet" type="button" :disabled="busy" @click="editing = undefined">Cancelar</button>
        </div>
      </form>
      <section v-if="tournament.rounds.length" class="tournament-bracket" aria-label="Rondas del torneo" tabindex="0">
        <section v-for="round in tournament.rounds" :key="round.number" class="tournament-round">
          <h3>{{ roundTitle(round.number, tournament.rounds.length) }}</h3>
          <article v-for="match in round.matches" :key="match.number" class="tournament-match">
            <h4>Partido {{ match.number }} <span>{{ matchStates[match.status] }}</span></h4>
            <ul>
              <li v-for="(participant, side) in [match.first, match.second]" :key="side"
                :class="{ 'match-winner': participant && participant.id === match.winner_id }">
                <span>{{ participant?.name ?? (match.status === 'bye' ? 'Pase directo' : 'Por definir') }}</span>
                <Trophy v-if="participant && participant.id === match.winner_id" :size="15" role="img" aria-label="Ganador" />
              </li>
            </ul>
            <p v-if="match.score" class="tournament-score">{{ match.score }}</p>
            <button v-if="tournament.can_manage && tournament.state === 'in_progress' && match.status === 'ready'"
              class="button secondary" type="button" :disabled="busy || !!editing" @click="selectMatch(round.number, match)">
              Registrar resultado
            </button>
          </article>
        </section>
      </section>
    </template>
  </dialog>
</template>

<style scoped>
.tournament-dialog { width: min(calc(100% - 1rem), 65rem); max-height: calc(100dvh - 1rem); color: var(--ink); border: 1px solid var(--line); border-radius: 1.25rem; padding: 1rem; }
.tournament-dialog::backdrop { background: #13254090; }
.tournament-header { display: flex; justify-content: space-between; gap: .7rem; align-items: center; margin-bottom: .7rem; }
.tournament-header h2 { overflow-wrap: anywhere; }
.tournament-registration { display: grid; gap: .75rem; justify-items: start; }
.tournament-champion { display: flex; flex-wrap: wrap; align-items: center; gap: .45rem; color: var(--ink); background: var(--light); border: 1px solid var(--line); padding: .65rem; border-radius: .7rem; }
.tournament-result { padding: .9rem; margin: .9rem 0; }
.tournament-bracket { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(13rem, 1fr); gap: .8rem; overflow-x: auto; overscroll-behavior-x: contain; padding: .4rem .2rem 1rem; }
.tournament-round { display: grid; align-content: start; gap: .65rem; }
.tournament-round h3 { padding: .45rem 0; }
.tournament-match { border: 1px solid var(--line); border-radius: .8rem; padding: .7rem; overflow-wrap: anywhere; }
.tournament-match h4 { margin: 0 0 .55rem; font-size: .9rem; display: flex; align-items: center; justify-content: space-between; gap: .4rem; }
.tournament-match h4 span { color: var(--muted); font-size: .78rem; }
.tournament-match ul { margin: .25rem 0; padding: 0; list-style: none; }
.tournament-match li { display: flex; align-items: center; justify-content: space-between; gap: .4rem; padding: .25rem .4rem; }
.tournament-match li svg { flex: none; }
.tournament-match .match-winner { background: var(--light); border-radius: .4rem; color: var(--blue); font-weight: 750; }
.tournament-score { font-size: .86rem; margin: .25rem 0; }
.tournament-match .button { margin-top: .55rem; width: 100%; }
@media (max-width: 480px) { .tournament-bracket { grid-auto-columns: minmax(13rem, 78%); } }
</style>
