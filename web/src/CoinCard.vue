<script setup lang="ts">
import { ref } from 'vue'
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
}
const themes = { ocean: 'Océano', night: 'Noche', jade: 'Jade' }
const preference = `wallnut.coin-card.${props.accountId}`
const savedTheme = localStorage.getItem(preference)
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
const times = new Intl.DateTimeFormat('es-CO', { timeStyle: 'short' })
const prefix = 'wallnut:coins:'
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function saveTheme() {
  localStorage.setItem(preference, theme.value)
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
}

async function act(action: () => Promise<void>) {
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

function generate() {
  void act(async () => {
    if (!charge.value || charge.value.amount !== amount.value) {
      charge.value = { id: crypto.randomUUID(), amount: amount.value }
    }
    const created = await api<Payment>('/coin-payments', { token: props.token, method: 'POST', data: charge.value })
    const { toDataURL } = await import('qrcode')
    qr.value = await toDataURL(prefix + created.id, { width: 240, margin: 3 })
    payment.value = created
  })
}

function parseScan(value: string) {
  const id = value.slice(prefix.length)
  return value.startsWith(prefix) && uuid.test(id) ? id : undefined
}

function inspect() {
  const id = parseScan(code.value.trim()) ?? code.value.trim()
  payment.value = undefined
  if (!uuid.test(id)) {
    problem.value = 'Ingresa un código de pago válido.'
    return
  }
  void act(async () => {
    payment.value = await api<Payment>(`/coin-payments/${id}`, { token: props.token })
  })
}

function scanned(value: string) {
  code.value = value
  scanning.value = false
  inspect()
}

function refresh(id: string) {
  void act(async () => {
    payment.value = await api<Payment>(`/coin-payments/${id}`, { token: props.token })
    if (payment.value.status === 'paid') emit('changed')
  })
}

function pay(id: string) {
  void act(async () => {
    payment.value = await api<Payment>(`/coin-payments/${id}/pay`, { token: props.token, method: 'POST' })
    notice.value = 'Pago de Coins registrado.'
    emit('changed')
  })
}
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
      <template v-if="mode === 'receive' && payment?.status === 'pending'">
        <img class="coin-qr" :src="qr" width="240" height="240" alt="QR para cobrar Ardi Coins" />
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
        <p v-if="payment.status === 'paid'" class="success" role="status">Solicitud pagada · {{ payment.amount }} Coins</p>
        <p v-else-if="payment.status === 'expired'" class="state-note" role="status">La solicitud venció.</p>
        <template v-else-if="mode === 'pay'">
          <p><strong>{{ payment.recipient }}</strong> solicita <strong>{{ payment.amount }} Ardi Coins</strong>.</p>
          <button v-if="payment.can_pay" type="button" class="button primary" :disabled="busy" @click="pay(payment.id)">Confirmar pago</button>
          <p v-else class="state-note">Comparte esta solicitud para que otro estudiante pueda pagarla.</p>
        </template>
        <button v-if="mode && (mode === 'pay' || payment.status !== 'pending')" type="button" class="button quiet"
          :disabled="busy" @click="open(mode)">Empezar de nuevo</button>
      </template>
      <p v-if="problem" class="error" role="alert">{{ problem }}</p>
      <p v-if="notice" class="success" role="status">{{ notice }}</p>
    </div>
  </section>
</template>
