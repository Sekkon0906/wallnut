<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { History } from '@lucide/vue'
import { api, errorText, RequestError, type WalletMovement } from './client'

type Currency = 'all' | 'points' | 'coins'
type Balances = { points: number; coins: number; reserved_points: number }
interface Ledger {
  balances: Balances
  summary: {
    generated_at: string
    credited_points: number
    spent_points: number
    credited_coins: number
    spent_coins: number
    points_difference: number
    coins_difference: number
  }
  movements: WalletMovement[]
  next_cursor: Pick<WalletMovement, 'id' | 'kind' | 'created_at'> | null
}

const props = defineProps<{ token: string; revision: number }>()
const emit = defineEmits<{ expired: []; updated: [balances: Balances] }>()
const ledger = ref<Ledger>()
const movements = ref<WalletMovement[]>([])
const currency = ref<Currency>('all')
const loading = ref(false)
const problem = ref('')
const filters: { value: Currency; label: string }[] = [
  { value: 'all', label: 'Todos' }, { value: 'points', label: 'Points' }, { value: 'coins', label: 'Coins' },
]
const labels = {
  evidence_reward: 'Evidencia aprobada', goal_coins: 'Meta verificada',
  coin_conversion: 'Canje de Coins a Points', grade_redemption: 'Canje académico',
  ardy_purchase: 'Compra para tu Ardy', ardy_nut: 'Compra de una nuez',
  coin_sent: 'Pago de Ardi Coins', coin_received: 'Coins recibidos',
}
const numbers = new Intl.NumberFormat('es-CO')
const signed = new Intl.NumberFormat('es-CO', { signDisplay: 'exceptZero' })
const dates = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota' })
let revision = 0
let active = true
let failedAppend = false

async function load(append = false) {
  if (append && (loading.value || !ledger.value?.next_cursor)) return
  const current = ++revision
  const query = new URLSearchParams({ currency: currency.value })
  if (append && ledger.value?.next_cursor) {
    const cursor = ledger.value.next_cursor
    query.set('before', cursor.created_at)
    query.set('before_id', cursor.id)
    query.set('before_kind', cursor.kind)
  }
  loading.value = true
  problem.value = ''
  failedAppend = append
  try {
    const value = await api<Ledger>(`/wallet/history?${query}`, { token: props.token })
    if (!active || current !== revision) return
    ledger.value = value
    movements.value = append ? [...movements.value, ...value.movements] : value.movements
    emit('updated', value.balances)
  } catch (error) {
    if (!active || current !== revision) return
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    if (active && current === revision) loading.value = false
  }
}

function filter(value: Currency) {
  if (currency.value === value) return
  currency.value = value
  ledger.value = undefined
  movements.value = []
  void load()
}

onMounted(() => load())
watch(() => props.revision, () => load())
onBeforeUnmount(() => { active = false })
</script>

<template>
  <section class="wallet-section wallet-ledger" aria-labelledby="wallet-movements">
    <div class="section-heading">
      <h2 id="wallet-movements"><History :size="22" aria-hidden="true" /> Movimientos</h2>
      <button class="button quiet" type="button" :disabled="loading" @click="load()">Actualizar movimientos</button>
    </div>
    <template v-if="ledger">
      <dl class="wallet-ledger-totals">
        <div class="tile"><dt>Ardi Points</dt><dd>{{ numbers.format(ledger.balances.points) }} disponibles</dd>
          <dd>{{ numbers.format(ledger.summary.credited_points) }} recibidos · {{ numbers.format(ledger.summary.spent_points) }} usados</dd>
          <dd>{{ numbers.format(ledger.balances.reserved_points) }} en reserva para canjes</dd>
        </div>
        <div class="tile"><dt>Ardi Coins</dt><dd>{{ numbers.format(ledger.balances.coins) }} disponibles</dd>
          <dd>{{ numbers.format(ledger.summary.credited_coins) }} recibidos · {{ numbers.format(ledger.summary.spent_coins) }} usados</dd>
        </div>
      </dl>
      <p v-if="ledger.summary.points_difference || ledger.summary.coins_difference" class="error" role="alert">
        Hay una diferencia entre los movimientos y el saldo. Actualiza la consulta y comunícala a Administración si continúa.
      </p>
      <p class="state-note">Resumen total de tu billetera. Los filtros solo cambian la lista.</p>
      <p class="wallet-history-cut">Consultado el <time :datetime="ledger.summary.generated_at">{{ dates.format(new Date(ledger.summary.generated_at)) }}</time></p>
    </template>
    <div class="wallet-history-filters" role="group" aria-label="Filtrar movimientos por unidad">
      <button v-for="option in filters" :key="option.value" class="button secondary" type="button"
        :aria-pressed="currency === option.value" @click="filter(option.value)">{{ option.label }}</button>
    </div>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="loading" class="state-note" role="status">Consultando movimientos…</p>
    <p v-if="ledger && !movements.length" class="tile state-note">
      {{ currency === 'all' ? 'Aún no tienes movimientos.' : `Aún no tienes movimientos de ${currency === 'points' ? 'Points' : 'Coins'}.` }}
    </p>
    <ol v-if="movements.length" class="tile wallet-history">
      <li v-for="movement in movements" :key="`${movement.kind}-${movement.id}`">
        <div class="wallet-history-context">
          <h3>{{ labels[movement.kind] }}</h3>
          <p>{{ movement.course }}<template v-if="movement.workshop"> · {{ movement.workshop }}</template></p>
          <time :datetime="movement.created_at">{{ dates.format(new Date(movement.created_at)) }}</time>
          <details class="wallet-history-reference"><summary>Referencia</summary><code>{{ movement.id }}</code></details>
        </div>
        <ul class="wallet-deltas">
          <li v-if="movement.points" :class="{ 'delta-positive': movement.points > 0 }">{{ signed.format(movement.points) }} Points</li>
          <li v-if="movement.coins" :class="{ 'delta-positive': movement.coins > 0 }">{{ signed.format(movement.coins) }} Coins</li>
        </ul>
      </li>
    </ol>
    <button v-if="problem" class="button secondary wallet-history-more" type="button" :disabled="loading" @click="load(failedAppend)">Reintentar consulta</button>
    <button v-else-if="ledger?.next_cursor" class="button secondary wallet-history-more" type="button" :disabled="loading" @click="load(true)">Ver movimientos anteriores</button>
  </section>
</template>

<style scoped>
.wallet-ledger-totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 10px; margin: 0; }
.wallet-ledger-totals dt { font-weight: 750; color: var(--blue); }
.wallet-ledger-totals dd { margin: 6px 0 0; overflow-wrap: anywhere; }
.wallet-ledger-totals dd + dd { color: var(--muted); font-size: .86rem; }
.wallet-history-cut { color: var(--muted); font-size: .84rem; }
.wallet-history-filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }
.wallet-history-filters [aria-pressed=true] { background: var(--blue); color: white; }
.wallet-history-context { min-width: 0; }
.wallet-history-reference { margin-top: 6px; color: var(--muted); font-size: .8rem; }
.wallet-history-reference summary { cursor: pointer; }
.wallet-history-reference code { display: block; overflow-wrap: anywhere; margin-top: 5px; }
.wallet-history-more { margin-top: 12px; }
@media (max-width: 480px) { .wallet-history > li { flex-wrap: wrap; } .wallet-deltas { margin-left: auto; } }
</style>
