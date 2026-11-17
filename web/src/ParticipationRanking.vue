<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, errorText, RequestError } from './client'
import type { RankingEntry } from './ardy'
import ArdyPortrait from './ArdyPortrait.vue'

const props = defineProps<{ token: string; isStudent: boolean }>()
const emit = defineEmits<{ expired: []; edit: [] }>()
const ranking = ref<{ entries: RankingEntry[]; me: RankingEntry | null }>()
const busy = ref(false)
const problem = ref('')
const format = new Intl.NumberFormat('es-CO')

async function load() {
  busy.value = true
  problem.value = ''
  try {
    ranking.value = await api('/participation-ranking', { token: props.token })
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}
onMounted(load)
</script>

<template>
  <section class="ardy-section" aria-labelledby="ranking-heading">
    <div class="section-heading">
      <div>
        <h1 id="ranking-heading">Ranking de participación</h1>
        <p>Ordenado por Points ganados en talleres con evidencia aprobada.</p>
      </div>
      <button v-if="isStudent" class="button secondary" @click="emit('edit')">Mi Ardy y visibilidad</button>
    </div>
    <p v-if="busy" role="status">Cargando el ranking…</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <button v-if="problem" class="button quiet" @click="load">Reintentar</button>
    <p v-if="ranking && !ranking.entries.length" class="tile state-note">El ranking se abre con las primeras participaciones verificadas de estudiantes que elijan aparecer.</p>
    <ol v-if="ranking?.entries.length" class="ranking-list">
      <li v-for="row in ranking.entries" :key="row.student_id" :value="row.position" class="tile ranking-row"
        :class="{ 'ranking-me': row.is_me }">
        <span class="rank-number" :aria-label="'Puesto ' + row.position">{{ row.position }}</span>
        <ArdyPortrait :avatar="row.avatar" small />
        <div><strong>{{ row.display_name }}<span v-if="row.is_me"> · Tú</span></strong>
          <p>{{ row.activities }} {{ row.activities === 1 ? 'participación' : 'participaciones' }}</p></div>
        <strong class="rank-points">{{ format.format(row.points) }} Points</strong>
      </li>
    </ol>
    <p v-if="ranking?.me && !ranking.entries.some(row => row.is_me)" class="tile">
      Tu puesto es {{ ranking.me.position }}, con {{ format.format(ranking.me.points) }} Points.
    </p>
  </section>
</template>
