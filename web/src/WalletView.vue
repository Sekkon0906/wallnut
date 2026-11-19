<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowRight, Target } from '@lucide/vue'
import { api, errorText, RequestError, type Wallet, type WalletConversion } from './client'
import CoinCard from './CoinCard.vue'
import WalletHistory from './WalletHistory.vue'

const props = defineProps<{ token: string; accountId: string; name: string }>()
const emit = defineEmits<{ expired: []; academic: []; shop: [] }>()
const wallet = ref<Wallet>()
const loading = ref(false)
const converting = ref('')
const problem = ref('')
const notice = ref('')
const historyRevision = ref(0)
let active = true
let loadRevision = 0
const numbers = new Intl.NumberFormat('es-CO')

function handleError(error: unknown) {
  if (!active) return
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else problem.value = errorText(error)
}

async function load() {
  const revision = ++loadRevision
  loading.value = true
  problem.value = ''
  try {
    const value = await api<Wallet>('/wallet', { token: props.token })
    if (active && revision === loadRevision) {
      wallet.value = value
      historyRevision.value++
    }
  } catch (error) {
    if (revision === loadRevision) handleError(error)
  } finally {
    if (active && revision === loadRevision) loading.value = false
  }
}
onMounted(load)
onBeforeUnmount(() => { active = false })

async function convert(goal: WalletConversion) {
  if (converting.value || goal.converted) return
  converting.value = goal.evidence_id
  problem.value = ''
  notice.value = ''
  try {
    await api(`/workshops/${goal.workshop_id}/evidence/${goal.evidence_id}/convert`, {
      token: props.token, method: 'POST',
    })
    if (!active) return
    notice.value = 'Canje registrado.'
    await load()
  } catch (error) {
    handleError(error)
  } finally {
    converting.value = ''
  }
}

function updateBalances(balances: Pick<Wallet, 'points' | 'coins' | 'reserved_points'>) {
  if (wallet.value) wallet.value = { ...wallet.value, ...balances }
}
</script>

<template>
  <section class="economy-page" aria-labelledby="wallet-heading">
    <div class="section-heading">
      <div>
        <h1 id="wallet-heading">Billetera</h1>
        <p>Consulta tus saldos y el origen de cada abono.</p>
      </div>
      <button v-if="wallet" class="button quiet" type="button" :disabled="loading || !!converting" @click="load">
        Actualizar saldo
      </button>
    </div>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="loading && !wallet" class="state-note" role="status">Cargando tu billetera…</p>
    <button v-if="problem && !wallet" class="button secondary" type="button" @click="load">Reintentar</button>
    <template v-if="wallet">
      <div class="wallet-balances">
        <article class="tile wallet-balance">
          <img src="/ardi-points.png" alt="" width="80" height="80" />
          <div><h2>Ardi Points disponibles</h2><p>{{ numbers.format(wallet.points) }}</p></div>
        </article>
      </div>
      <p v-if="wallet.reserved_points" class="state-note">
        {{ numbers.format(wallet.reserved_points) }} Points reservados en solicitudes académicas.
      </p>
      <button class="button secondary academic-shortcut" type="button" @click="emit('academic')">
        Ver canjes académicos <ArrowRight :size="16" aria-hidden="true" />
      </button>
      <CoinCard :token="token" :account-id="accountId" :name="name" :coins="wallet.coins"
        @changed="load" @expired="emit('expired')" />
      <button class="button secondary academic-shortcut" type="button" @click="emit('shop')">
        Ir a la tienda de Ardy <ArrowRight :size="16" aria-hidden="true" />
      </button>

      <section class="wallet-section" aria-labelledby="wallet-goals">
        <h2 id="wallet-goals"><Target :size="22" aria-hidden="true" /> Canjes por metas verificadas</h2>
        <p v-if="!wallet.conversions.length" class="tile state-note">Los canjes aparecerán cuando un docente verifique una meta.</p>
        <article v-for="goal in wallet.conversions" :key="goal.evidence_id" class="tile wallet-conversion">
          <div>
            <span class="wallet-context">{{ goal.course }} · {{ goal.workshop }}</span>
            <h3>{{ goal.goal }}</h3>
            <p>{{ numbers.format(goal.coin_cost) }} Coins <ArrowRight :size="16" aria-label="por" /> {{ numbers.format(goal.points) }} Points</p>
            <small v-if="!goal.converted && wallet.coins < goal.coin_cost">Saldo insuficiente de Coins.</small>
          </div>
          <span v-if="goal.converted" class="badge badge-confirmed">Canjeado</span>
          <button v-else class="button primary" type="button" :disabled="!!converting || loading || wallet.coins < goal.coin_cost"
            @click="convert(goal)">{{ converting === goal.evidence_id ? 'Canjeando…' : 'Canjear por Points' }}</button>
        </article>
      </section>

      <WalletHistory :token="token" :revision="historyRevision" @expired="emit('expired')" @updated="updateBalances" />
    </template>
  </section>
</template>
