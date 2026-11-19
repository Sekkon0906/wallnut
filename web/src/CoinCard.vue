<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { CreditCard, QrCode, ScanLine } from '@lucide/vue'
import { api, errorText, RequestError } from './client'
import QrScanner from './QrScanner.vue'

const props = defineProps<{ token: string; accountId: string; name: string; coins: number }>()
const emit = defineEmits<{ expired: []; changed: [] }>()
type Payment = {
  id: string
  recipient: string
  amount: number
  status: 'pending' | 'paid' | 'expired'
  expires_at: string
  can_pay: boolean
  is_recipient: boolean
  paid_by_me: boolean
  paid_at: string | null
}
const themes = { ocean: 'Océano', night: 'Noche', jade: 'Jade' }
const preference = `wallnut.coin-card.${props.accountId}`
let savedTheme: string | null = null
try { savedTheme = localStorage.getItem(preference) } catch { /* La tarjeta usa su color inicial. */ }
const theme = ref(savedTheme === 'night' || savedTheme === 'jade' ? savedTheme : 'ocean')
const mode = ref<'receive' | 'pay'>()
const amount = ref(1)
const code = ref('')
const charge = ref<{ id: string; amount: number }>()
const payment = ref<Payment>()
const qr = ref('')
const scanning = ref(false)
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const recent = ref<Payment[]>([])
const recentLoading = ref(false)
const recentProblem = ref('')
const uncertain = ref('')
const now = ref(Date.now())
const paymentStatus = computed(() => payment.value ? statusOf(payment.value) : undefined)
const times = new Intl.DateTimeFormat('es-CO', { timeStyle: 'short', timeZone: 'America/Bogota' })
const dates = new Intl.DateTimeFormat('es-CO', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Bogota' })
const states = { pending: 'Pendiente', paid: 'Pagada', expired: 'Vencida' }
const prefix = 'wallnut:coins:'
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
let active = true
let recentRevision = 0
let timer: ReturnType<typeof setInterval>

function statusOf(value: Payment) {
  return value.status === 'pending' && Date.parse(value.expires_at) <= now.value ? 'expired' : value.status
}

function saveTheme() {
  try { localStorage.setItem(preference, theme.value) } catch { /* El color se conserva en esta vista. */ }
}

function open(value: typeof mode.value) {
  mode.value = value
  payment.value = undefined
  charge.value = undefined
  qr.value = ''
  code.value = ''
  problem.value = ''
  notice.value = ''
  scanning.value = false
  uncertain.value = ''
}

async function act(action: () => Promise<void>) {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    await action()
  } catch (error) {
    if (!active) return
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    if (active) busy.value = false
  }
}

async function loadRecent() {
  const revision = ++recentRevision
  recentLoading.value = true
  recentProblem.value = ''
  try {
    const rows = await api<Payment[]>('/coin-payments', { token: props.token })
    if (active && revision === recentRevision) recent.value = rows
  } catch (error) {
    if (!active || revision !== recentRevision) return
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else recentProblem.value = errorText(error)
  } finally {
    if (active && revision === recentRevision) recentLoading.value = false
  }
}

async function showQR(value: Payment) {
  const { toDataURL } = await import('qrcode')
  const image = await toDataURL(prefix + value.id, { width: 240, margin: 3 })
  if (active) qr.value = image
}

function generate() {
  void act(async () => {
    if (!charge.value || charge.value.amount !== amount.value) {
      charge.value = { id: crypto.randomUUID(), amount: amount.value }
    }
    const created = await api<Payment>('/coin-payments', { token: props.token, method: 'POST', data: charge.value })
    if (!active) return
    payment.value = created
    if (active && statusOf(created) === 'pending') await showQR(created)
    await loadRecent()
  })
}

function parseScan(value: string) {
  const id = value.slice(prefix.length)
  return value.startsWith(prefix) && uuid.test(id) ? id : undefined
}

function inspect() {
  if (busy.value) return
  const id = parseScan(code.value.trim()) ?? code.value.trim()
  payment.value = undefined
  if (!uuid.test(id)) {
    problem.value = 'Ingresa un código de pago válido.'
    return
  }
  void act(async () => {
    const result = await api<Payment>(`/coin-payments/${id}`, { token: props.token })
    if (active) payment.value = result
  })
}

function scanned(value: string) {
  code.value = value
  scanning.value = false
  inspect()
}

function refresh(id: string) {
  void act(async () => {
    const result = await api<Payment>(`/coin-payments/${id}`, { token: props.token })
    if (!active) return
    payment.value = result
    uncertain.value = ''
    if (result.status === 'paid') emit('changed')
    else if (mode.value === 'pay' && statusOf(result) === 'pending') notice.value = 'La solicitud sigue pendiente. Puedes confirmar el pago.'
    await loadRecent()
  })
}

function pay(id: string) {
  void act(async () => {
    let result: Payment
    try {
      result = await api<Payment>(`/coin-payments/${id}/pay`, { token: props.token, method: 'POST' })
    } catch (error) {
      if (active && (!(error instanceof RequestError) || error.status >= 500)) uncertain.value = id
      throw error
    }
    if (!active) return
    payment.value = result
    uncertain.value = ''
    notice.value = 'Pago de Coins registrado.'
    emit('changed')
    await loadRecent()
  })
}

function resume(entry: Payment) {
  if (busy.value) return
  open(entry.is_recipient ? 'receive' : 'pay')
  void act(async () => {
    const current = await api<Payment>(`/coin-payments/${entry.id}`, { token: props.token })
    if (!active) return
    payment.value = current
    if (current.is_recipient && statusOf(current) === 'pending') await showQR(current)
  })
}

onMounted(() => {
  void loadRecent()
  timer = setInterval(() => { now.value = Date.now() }, 1000)
})
onBeforeUnmount(() => {
  active = false
  clearInterval(timer)
})
</script>

<template>
  <section class="coin-wallet" aria-label="Tarjeta virtual">
    <div class="coin-card" :data-theme="theme">
      <div><CreditCard :size="24" aria-hidden="true" /> <span>Wallnut</span></div>
      <img src="/ardi-coins.png" width="74" height="74" alt="" />
      <div class="coin-card-balance"><strong>{{ coins.toLocaleString('es-CO') }}</strong><span>Ardi Coins</span></div>
      <span class="coin-card-name">{{ name }}</span>
      <small>Uso dentro de Wallnut · Sin valor monetario</small>
    </div>
    <div class="tile coin-tools form-stack">
      <label>Color de la tarjeta
        <select v-model="theme" @change="saveTheme">
          <option v-for="(label, value) in themes" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <div class="workshop-actions">
        <button type="button" class="button secondary" :disabled="busy" :aria-pressed="mode === 'receive'" @click="open('receive')">
          <QrCode :size="19" aria-hidden="true" /> Recibir Coins
        </button>
        <button type="button" class="button primary" :disabled="busy" :aria-pressed="mode === 'pay'" @click="open('pay')">
          <ScanLine :size="19" aria-hidden="true" /> Pagar con QR
        </button>
      </div>
      <form v-if="mode === 'receive' && !payment" class="form-stack" @submit.prevent="generate">
        <label>Cantidad de Coins <input v-model.number="amount" type="number" min="1" max="1000" step="1" required :disabled="busy" /></label>
        <button class="button primary" :disabled="busy">Generar QR de cobro</button>
      </form>
      <template v-if="mode === 'receive' && payment && paymentStatus === 'pending'">
        <img v-if="qr" class="coin-qr" :src="qr" width="240" height="240" alt="QR para cobrar Ardi Coins" />
        <p>Solicitud de {{ payment.amount }} Coins · Vence a las {{ times.format(new Date(payment.expires_at)) }}</p>
        <label>Código de pago <input :value="payment.id" readonly @focus="($event.target as HTMLInputElement).select()" /></label>
        <button type="button" class="button secondary" :disabled="busy" @click="refresh(payment.id)">Consultar estado</button>
      </template>
      <template v-if="mode === 'pay' && !payment">
        <QrScanner v-if="scanning" :parse="parseScan" instruction="Enfoca el QR de la solicitud de Coins."
          mismatch="Este QR no corresponde a una solicitud de Coins." @code="scanned" @close="scanning = false" />
        <form v-else class="form-stack" @submit.prevent="inspect">
          <button type="button" class="button secondary" :disabled="busy" @click="scanning = true">Abrir cámara</button>
          <label>Código de pago <input v-model="code" required maxlength="50" autocomplete="off" :disabled="busy" /></label>
          <button class="button primary" :disabled="busy">Revisar solicitud</button>
        </form>
      </template>
      <template v-if="payment">
        <template v-if="uncertain">
          <p class="state-note" role="status">Consulta el resultado del intento anterior para continuar.</p>
          <button type="button" class="button secondary" :disabled="busy" @click="refresh(payment.id)">Consultar resultado</button>
        </template>
        <p v-else-if="paymentStatus === 'paid'" class="success" role="status">
          <template v-if="payment.paid_by_me">Pagaste {{ payment.amount }} Coins a {{ payment.recipient }}</template>
          <template v-else-if="payment.is_recipient">Solicitud pagada · {{ payment.amount }} Coins recibidos</template>
          <template v-else>Esta solicitud ya fue pagada por otra cuenta</template>
          <span v-if="payment.paid_at">{{ ` · ${dates.format(new Date(payment.paid_at))}` }}</span>
        </p>
        <p v-else-if="paymentStatus === 'expired'" class="state-note" role="status">La solicitud venció.</p>
        <template v-else-if="mode === 'pay'">
          <p><strong>{{ payment.recipient }}</strong> solicita <strong>{{ payment.amount }} Ardi Coins</strong>.</p>
          <button v-if="payment.can_pay" type="button" class="button primary" :disabled="busy || coins < payment.amount" @click="pay(payment.id)">Confirmar pago</button>
          <p v-else class="state-note">Comparte esta solicitud para que otro estudiante pueda pagarla.</p>
          <p v-if="payment.can_pay && coins < payment.amount" class="state-note">Tu saldo de Coins es insuficiente.</p>
        </template>
        <button v-if="mode === 'pay' && payment.status !== 'paid' && !uncertain" type="button"
          class="button secondary" :disabled="busy" @click="refresh(payment.id)">Consultar estado</button>
        <button v-if="mode && (mode === 'pay' || paymentStatus !== 'pending')" type="button" class="button quiet"
          :disabled="busy" @click="open(mode)">Empezar de nuevo</button>
      </template>
      <p v-if="problem" class="error" role="alert">{{ problem }}</p>
      <p v-if="notice" class="success" role="status">{{ notice }}</p>
    </div>
    <section class="tile recent-payments" aria-labelledby="recent-payments-title">
      <div class="section-heading">
        <h2 id="recent-payments-title">Solicitudes recientes</h2>
        <button type="button" class="button quiet" :disabled="recentLoading || busy" @click="loadRecent">Actualizar solicitudes</button>
      </div>
      <p v-if="recentProblem" class="error" role="alert">{{ recentProblem }}</p>
      <p v-if="recentLoading && !recent.length" role="status">Consultando tus solicitudes…</p>
      <p v-else-if="!recentProblem && !recent.length">Aquí aparecerán tus cobros y pagos de Coins.</p>
      <ul v-if="recent.length">
        <li v-for="entry in recent" :key="entry.id">
          <div>
            <strong>{{ entry.is_recipient ? 'Cobro de' : 'Pago de' }} {{ entry.amount }} Coins</strong>
            <p v-if="!entry.is_recipient">A {{ entry.recipient }}</p>
            <p>{{ states[statusOf(entry)] }} · {{ dates.format(new Date(entry.paid_at ?? entry.expires_at)) }}</p>
          </div>
          <button type="button" class="button secondary" :disabled="busy" @click="resume(entry)">Ver solicitud</button>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.recent-payments { grid-column: 1 / -1; display: grid; gap: .75rem; }
.recent-payments ul { list-style: none; margin: 0; padding: 0; }
.recent-payments li { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: .7rem; padding: .8rem 0; border-top: 1px solid var(--line); }
.recent-payments li p { margin: .15rem 0 0; font-size: .88rem; }
</style>
