<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, errorText, RequestError, type Workshop, type WorkshopEconomy } from './client'

const props = defineProps<{ token: string; workshop: Workshop }>()
const emit = defineEmits<{ expired: [] }>()
const economy = ref<WorkshopEconomy | null>()
const loading = ref(false)
const saving = ref(false)
const problem = ref('')
const notice = ref('')
const enabled = ref(false)
const form = reactive({
  attendee_points: 0 as number | '',
  facilitator_points: 0 as number | '',
  goal_description: '',
  goal_coins: '' as number | '',
  coin_cost: '' as number | '',
  conversion_points: '' as number | '',
  points_scope: 'course_only' as WorkshopEconomy['points_scope'],
})

function sync(value: WorkshopEconomy | null) {
  economy.value = value
  form.attendee_points = value?.attendee_points ?? 0
  form.facilitator_points = value?.facilitator_points ?? 0
  form.goal_description = value?.goal_description ?? ''
  form.goal_coins = value?.goal_coins ?? ''
  form.coin_cost = value?.coin_cost ?? ''
  form.conversion_points = value?.conversion_points ?? ''
  form.points_scope = value?.points_scope ?? 'course_only'
  enabled.value = !!value?.goal_description
}

function handleError(error: unknown) {
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else problem.value = errorText(error)
}

const path = `/workshops/${props.workshop.id}/economy`
async function load() {
  if (loading.value) return
  loading.value = true
  problem.value = ''
  try {
    sync(await api<WorkshopEconomy | null>(path, { token: props.token }))
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function save() {
  if (saving.value) return
  saving.value = true
  notice.value = ''
  problem.value = ''
  try {
    const result = await api<WorkshopEconomy>(path, { token: props.token, method: 'PUT', data: {
      attendee_points: Number(form.attendee_points),
      facilitator_points: Number(form.facilitator_points),
      goal_description: enabled.value ? form.goal_description.trim() : null,
      goal_coins: enabled.value ? Number(form.goal_coins) : null,
      coin_cost: enabled.value ? Number(form.coin_cost) : null,
      conversion_points: enabled.value ? Number(form.conversion_points) : null,
      points_scope: form.points_scope,
    } })
    sync(result)
    notice.value = 'Recompensas guardadas.'
  } catch (error) {
    handleError(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="economy-dialog">
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="loading" class="state-note" role="status">Consultando recompensas…</p>
    <button v-if="problem && economy === undefined" type="button" class="button quiet" @click="load">
      Volver a consultar
    </button>

    <form v-if="workshop.can_manage && economy !== undefined" class="form-stack" @submit.prevent="save">
      <p>Los Points se acreditan desde tu cupo docente al aprobar la evidencia. Los valores quedan fijos después de la primera acreditación o validación de la meta.</p>
      <div class="economy-fields">
        <label>Points por asistir
          <input v-model.number="form.attendee_points" type="number" min="0" step="1" required />
        </label>
        <label>Points para el tallerista
          <input v-model.number="form.facilitator_points" type="number" min="0" step="1" required />
        </label>
      </div>

      <label>Uso académico de los Points
        <select v-model="form.points_scope">
          <option value="course_only">Solo el grupo de origen</option>
          <option value="accepted_courses">Grupo de origen y otros grupos que los acepten</option>
        </select>
      </label>

      <label class="check-label">
        <input v-model="enabled" type="checkbox" /> Habilitar meta y canje de Coins
      </label>
      <template v-if="enabled">
        <label>Meta académica que verificarás
          <textarea v-model.trim="form.goal_description" rows="3" maxlength="500" required></textarea>
        </label>
        <div class="economy-fields">
          <label>Coins al verificar
            <input v-model.number="form.goal_coins" type="number" min="1" step="1" required />
          </label>
          <label>Coins que cuesta el canje
            <input v-model.number="form.coin_cost" type="number" min="1" step="1" required />
          </label>
          <label>Points que entrega el canje
            <input v-model.number="form.conversion_points" type="number" min="1" step="1" required />
          </label>
        </div>
      </template>
      <button class="button primary" type="submit" :disabled="saving || loading">
        {{ saving ? 'Guardando…' : 'Guardar recompensas' }}
      </button>
    </form>

    <template v-else-if="!workshop.can_manage">
      <p v-if="economy === null" class="state-note">Este taller aún no tiene recompensas configuradas.</p>
      <div v-else-if="economy" class="form-stack">
        <dl class="reward-summary">
          <div><dt>Por asistir con evidencia aprobada</dt><dd>{{ economy.attendee_points }} Points</dd></div>
          <div><dt>Por facilitar con evidencia aprobada</dt><dd>{{ economy.facilitator_points }} Points</dd></div>
          <div><dt>Uso académico</dt><dd>{{ economy.points_scope === 'accepted_courses'
            ? 'Grupo de origen y otros grupos que los acepten' : 'Solo el grupo de origen' }}</dd></div>
        </dl>
        <section v-if="economy.goal_description" class="tile workshop-goal">
          <h3>Meta académica</h3>
          <p class="reflection">{{ economy.goal_description }}</p>
          <p>El docente otorga {{ economy.goal_coins }} Coins al verificarla. Luego podrás canjear {{ economy.coin_cost }} Coins por {{ economy.conversion_points }} Points en tu billetera.</p>
        </section>
      </div>
    </template>
  </section>
</template>
