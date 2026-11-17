<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { X } from '@lucide/vue'
import { api, errorText, RequestError } from './client'
import { rarityLabels, type ArdyItem, type Avatar, type Rarity } from './ardy'
import ArdyPortrait from './ArdyPortrait.vue'
import NutShell from './NutShell.vue'

type Opening = { id: string; taps: number; rarity: Rarity | null; reward: ArdyItem | null }
type Shop = { price: number; coins: number; odds: Record<Rarity, number>; latest: Opening | null }
const props = defineProps<{ token: string; avatar: Avatar; shopRevision: number }>()
const emit = defineEmits<{ expired: []; unlocked: [item: ArdyItem]; tryOn: [item: ArdyItem] }>()
const shop = ref<Shop>()
const opening = ref<Opening>()
const dialog = ref<HTMLDialogElement>()
const dialogOpen = ref(false)
const tapButton = ref<HTMLButtonElement>()
const resultTitle = ref<HTMLElement>()
const problem = ref('')
const busy = ref(false)
const confirming = ref(false)
let purchaseId: string | undefined
let loadRevision = 0
const percentages = new Intl.NumberFormat('es-CO', { style: 'percent', maximumFractionDigits: 2 })
const remaining = computed(() => Object.values(shop.value?.odds ?? {}).reduce((a, b) => a + b, 0))
const pending = computed(() => shop.value?.latest && shop.value.latest.taps < 3 ? shop.value.latest : undefined)
const look = computed(() => opening.value?.reward
  ? { ...props.avatar, [opening.value.reward.slot]: opening.value.reward.value } : props.avatar)

function handleError(error: unknown) {
  if (error instanceof RequestError && error.status === 401) emit('expired')
  else problem.value = errorText(error)
}

async function load() {
  const revision = ++loadRevision
  try {
    const current = await api<Shop>('/ardy-nuts', { token: props.token })
    if (revision === loadRevision) shop.value = current
  } catch (error) {
    if (revision === loadRevision) handleError(error)
  }
}

async function show(value: Opening) {
  opening.value = value
  problem.value = ''
  await nextTick()
  dialog.value?.showModal()
  dialogOpen.value = true
  if (value.reward) resultTitle.value?.focus()
  else tapButton.value?.focus()
}

async function buy() {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  try {
    purchaseId ??= crypto.randomUUID()
    const value = await api<Opening>('/ardy-nuts', { token: props.token, method: 'POST', data: { id: purchaseId } })
    purchaseId = undefined
    confirming.value = false
    await show(value)
    void load()
  } catch (error) {
    handleError(error)
    if (error instanceof RequestError && error.status === 409) {
      purchaseId = undefined
      confirming.value = false
      void load()
    }
  } finally {
    busy.value = false
  }
}

async function tap() {
  const current = opening.value
  if (!current || current.reward || busy.value) return
  busy.value = true
  problem.value = ''
  try {
    const value = await api<Opening>(`/ardy-nuts/${current.id}/tap`, {
      token: props.token, method: 'PUT', data: { step: current.taps + 1 },
    })
    opening.value = value
    if (value.reward) {
      emit('unlocked', value.reward)
      await nextTick()
      resultTitle.value?.focus()
    }
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}

function onClose() {
  dialogOpen.value = false
  if (shop.value && opening.value) shop.value = { ...shop.value, latest: opening.value }
  problem.value = ''
  void load()
}

function tryReward(item: ArdyItem) {
  dialog.value?.close()
  emit('tryOn', item)
}

onMounted(load)
watch(() => props.shopRevision, load)
</script>

<template>
  <article class="tile nut-offer" aria-labelledby="nut-heading">
    <div class="nut-offer-art"><NutShell :step="0" /></div>
    <div class="nut-offer-copy">
      <h3 id="nut-heading">Nuez sorpresa</h3>
      <p>Ábrela con tres toques y desbloquea una prenda para tu Ardy.</p>
      <template v-if="shop">
        <p class="nut-balance">Tienes {{ shop.coins }} Ardi Coins</p>
        <div class="workshop-actions">
          <button v-if="pending" class="button primary" type="button" @click="show(pending)">Continuar apertura</button>
          <button v-else-if="remaining && !confirming" class="button primary" type="button" :disabled="busy || shop.coins < shop.price"
            @click="confirming = true">Comprar nuez · {{ shop.price }} Coins</button>
          <template v-else-if="confirming">
            <button class="button primary" type="button" :disabled="busy" @click="buy">Confirmar {{ shop.price }} Coins</button>
            <button class="button quiet" type="button" :disabled="busy" @click="confirming = false">Cancelar</button>
          </template>
          <button v-if="!pending && shop.latest?.reward" class="button quiet" type="button"
            @click="show(shop.latest)">Ver último premio</button>
        </div>
        <p v-if="!pending && !remaining" class="nut-info">Ya tienes toda esta colección.</p>
        <p v-else-if="!pending && shop.coins < shop.price" class="nut-info">Saldo insuficiente para otra nuez.</p>
        <details v-if="!pending && remaining" class="nut-odds">
          <summary>Probabilidades de la próxima nuez</summary>
          <ul>
            <li v-for="(weight, rarity) in shop.odds" :key="rarity">
              <span>{{ rarityLabels[rarity] }}</span> <strong>{{ percentages.format(weight / remaining) }}</strong>
            </li>
          </ul>
          <p>Cada nuez trae una prenda distinta. Las probabilidades se ajustan al completar una rareza.</p>
        </details>
      </template>
      <p v-else-if="!problem" role="status">Cargando las nueces…</p>
      <p v-if="problem && !dialogOpen" class="error" role="alert">{{ problem }}</p>
      <button v-if="!shop && problem" type="button" class="button secondary" @click="load">Reintentar</button>
    </div>
  </article>

  <dialog ref="dialog" class="nut-dialog" aria-labelledby="nut-dialog-title"
    @close="onClose" @cancel="busy && $event.preventDefault()">
    <section v-if="opening" class="nut-opening">
      <header>
        <h2 id="nut-dialog-title">{{ opening.reward ? 'Nuez abierta' : 'Abre tu nuez' }}</h2>
        <button type="button" class="button quiet nut-close" aria-label="Cerrar apertura" :disabled="busy" @click="dialog?.close()">
          <X :size="22" aria-hidden="true" />
        </button>
      </header>
      <div class="nut-reveal" :data-step="opening.taps">
        <NutShell :step="opening.taps" :rarity="opening.rarity" />
        <ArdyPortrait v-if="opening.reward" :avatar="look" />
        <button v-else ref="tapButton" class="nut-tap" type="button" :aria-disabled="busy"
          :aria-label="`Golpear la nuez, toque ${opening.taps + 1} de 3`" @click="tap"></button>
      </div>
      <div v-if="opening.reward" class="nut-result">
        <p v-if="opening.rarity" class="nut-rarity" :data-rarity="opening.rarity">{{ rarityLabels[opening.rarity] }}</p>
        <h3 ref="resultTitle" tabindex="-1">{{ opening.reward.name }}</h3>
        <p>La prenda ya está en tu armario.</p>
        <button type="button" class="button primary" @click="tryReward(opening.reward)">Probar en Mi Ardy</button>
      </div>
      <div v-else class="nut-progress">
        <div class="nut-steps" aria-hidden="true">
          <i v-for="step in 3" :key="step" :class="{ cracked: opening.taps >= step }"></i>
        </div>
        <p role="status">
          {{ opening.taps }} de 3 toques
          <span v-if="opening.rarity">· Brillo {{ rarityLabels[opening.rarity].toLowerCase() }}</span>
        </p>
        <p>Toca la nuez para romperla.</p>
      </div>
      <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    </section>
  </dialog>
</template>

<style scoped>
.nut-offer { display: grid; grid-template-columns: minmax(9rem, .8fr) minmax(0, 1.35fr); overflow: hidden; }
.nut-offer-art { min-height: 13rem; background: radial-gradient(ellipse at center, #444170, #1e2444 68%); overflow: hidden; }
.nut-offer-copy { padding: 1.15rem; display: grid; align-content: center; gap: .65rem; }
.nut-balance { font-weight: 750; color: var(--ink); }
.nut-info, .nut-odds { font-size: .9rem; }
.nut-odds summary { cursor: pointer; color: var(--blue); font-weight: 675; }
.nut-odds ul { list-style: none; padding: 0; margin: .55rem 0; display: grid; gap: .35rem; }
.nut-odds li { display: flex; justify-content: space-between; max-width: 16rem; }
.nut-dialog {
  color: #f8faff;
  background: #151b34;
  border: 1px solid #ffffff30;
  border-radius: 24px;
  padding: 0;
  width: min(calc(100% - 1.5rem), 34rem);
  max-height: calc(100dvh - 1.5rem);
  box-shadow: 0 1.5rem 6rem #080d23a0;
}
.nut-dialog::backdrop { background: #070d21bd; }
.nut-opening { display: grid; text-align: center; }
.nut-opening header { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.15rem .25rem; }
.nut-opening header h2 { text-align: left; }
.nut-close { color: white; }
.nut-close:hover { color: var(--ink); }
.nut-reveal { display: grid; isolation: isolate; overflow: hidden; position: relative; height: clamp(11rem, 50dvh, 19rem); }
.nut-reveal .ardy-portrait {
  position: absolute;
  justify-self: center;
  align-self: center;
  width: auto;
  height: 100%;
  max-width: 100%;
  pointer-events: none;
  animation: nut-reward 460ms 160ms ease-out both;
}
.nut-tap { position: absolute; inset: .45rem; border: 0; border-radius: 14px; background: transparent; touch-action: manipulation; }
.nut-tap:focus-visible { outline-color: #b3d5ff; outline-offset: -3px; }
.nut-result, .nut-progress { display: grid; justify-items: center; gap: .55rem; padding: .4rem 1rem 1.3rem; }
.nut-opening p { color: #d8e1fa; }
.nut-opening p.error { margin: .25rem 1rem 1rem; color: #ffd0d0; background: #462649; }
.nut-result .nut-rarity { color: #f6f8ff; font-weight: 800; }
.nut-result .nut-rarity[data-rarity="special"] { color: #90f5dd; }
.nut-result .nut-rarity[data-rarity="epic"] { color: #e7b5fa; }
.nut-result .nut-rarity[data-rarity="legendary"] { color: #ffdd89; }
.nut-steps { display: flex; gap: .5rem; }
.nut-steps i { width: 2.2rem; height: .35rem; border-radius: 99px; background: #6a7696; }
.nut-steps .cracked { background: #e7ebff; }
@keyframes nut-reward {
  from { opacity: 0; transform: translateY(.8rem) scale(.86); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@media (prefers-reduced-motion: reduce) { .nut-reveal .ardy-portrait { animation: none; } }
@media (max-width: 49rem) {
  .nut-offer { grid-template-columns: 1fr; }
  .nut-offer-art { min-height: 10.5rem; }
}
</style>
