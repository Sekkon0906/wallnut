<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { api, errorText, RequestError } from './client'
import { avatarControls, careerLooks, defaultAvatar, rarityLabels, type ArdyItem, type ArdyProfile } from './ardy'
import ArdyPortrait from './ArdyPortrait.vue'
import NutShop from './NutShop.vue'
import CampusProfileEditor from './CampusProfileEditor.vue'

const props = defineProps<{ token: string; displayName: string }>()
const emit = defineEmits<{ expired: [] }>()
const profile = ref<ArdyProfile>()
const avatar = ref({ ...defaultAvatar })
const visible = ref(false)
const career = ref('')
const items = ref<ArdyItem[]>([])
const shopRevision = ref(0)
const heading = ref<HTMLElement>()
const purchasing = ref('')
const confirmItem = ref<ArdyItem>()
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const changed = computed(() => !!profile.value && (
  Object.keys(defaultAvatar).some(key => {
    const field = key as keyof typeof defaultAvatar
    return avatar.value[field] !== profile.value?.avatar[field]
  }) || visible.value !== profile.value.show_in_ranking || (career.value.trim() || null) !== profile.value.career
))

function assign(value: ArdyProfile) {
  profile.value = value
  avatar.value = { ...value.avatar }
  visible.value = value.show_in_ranking
  career.value = value.career ?? ''
}

async function run(save: boolean) {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    const value = await api<ArdyProfile>('/my-ardy', save ? {
      token: props.token, method: 'PUT',
      data: { avatar: avatar.value, show_in_ranking: visible.value, career: career.value.trim() || null },
    } : { token: props.token })
    assign(value)
    if (save) notice.value = 'Guardaste tu Ardy.'
    else items.value = await api<ArdyItem[]>('/ardy-shop', { token: props.token })
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

async function buy(item: ArdyItem) {
  if (purchasing.value) return
  purchasing.value = item.id
  problem.value = ''
  notice.value = ''
  try {
    const bought = await api<ArdyItem>(`/ardy-shop/${item.id}`, { token: props.token, method: 'POST' })
    items.value = items.value.map(entry => entry.id === bought.id ? bought : entry)
    shopRevision.value++
    avatar.value[bought.slot] = bought.value
    confirmItem.value = undefined
    notice.value = 'Artículo adquirido. Guarda tu Ardy para equiparlo.'
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    purchasing.value = ''
  }
}

function unlock(item: ArdyItem) {
  if (!items.value.some(entry => entry.id === item.id)) items.value = [...items.value, item]
}

async function tryOn(item: ArdyItem) {
  unlock(item)
  avatar.value[item.slot] = item.value
  notice.value = 'Prenda en vista previa. Guarda tu Ardy para equiparla.'
  await nextTick()
  heading.value?.focus()
}

function applyLook(event: Event) {
  const select = event.target as HTMLSelectElement
  const look = careerLooks.find(entry => entry.name === select.value)
  if (look) avatar.value = { ...defaultAvatar, ...look.details }
  select.value = ''
}
onMounted(() => run(false))
</script>

<template>
  <section class="ardy-section" aria-labelledby="ardy-heading">
    <h1 id="ardy-heading" ref="heading" tabindex="-1">Mi Ardy</h1>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="busy && !profile" role="status">Cargando tu Ardy…</p>
    <button v-if="problem && !profile" class="button secondary" @click="run(false)">Reintentar</button>
    <form v-if="profile" class="ardy-editor" @submit.prevent="run(true)">
      <figure class="ardy-preview">
        <ArdyPortrait :avatar="avatar" />
        <figcaption>Vista previa de tu Ardy</figcaption>
      </figure>
      <fieldset class="tile form-stack ardy-controls" :disabled="busy || !!purchasing">
        <legend>Personalización</legend>
        <label>Tu carrera
          <input v-model="career" placeholder="Ej. Ingeniería de Sistemas" minlength="2" maxlength="100" />
        </label>
        <label>Apariencia por área
          <select value="" @change="applyLook">
            <option value="" disabled>Prueba un estilo inicial</option>
            <option v-for="look in careerLooks" :key="look.name">{{ look.name }}</option>
          </select>
        </label>
        <label>Altura · {{ avatar.height }} %
          <input v-model.number="avatar.height" type="range" min="85" max="115" />
        </label>
        <div class="ardy-options">
          <label v-for="control in avatarControls" :key="control.key">{{ control.label }}
            <select v-model="avatar[control.key]">
              <option v-for="[value, label] in control.options" :key="value" :value="value">{{ label }}</option>
              <option v-for="item in items.filter(entry => entry.owned && entry.slot === control.key)"
                :key="item.id" :value="item.value">{{ item.name }}</option>
            </select>
          </label>
        </div>
        <label class="rank-visibility">
          <input v-model="visible" type="checkbox" />
          Mostrar mi nombre y mi Ardy en el ranking
        </label>
        <div class="workshop-actions">
          <button class="button primary" type="submit" :disabled="busy || !changed">Guardar mi Ardy</button>
          <button class="button quiet" type="button" @click="avatar = { ...defaultAvatar }; notice = ''">Restablecer apariencia</button>
        </div>
      </fieldset>
    </form>
    <CampusProfileEditor v-if="profile" :token="token" :display-name="displayName" :ardy="profile" @expired="emit('expired')" />
    <section v-if="profile" class="wallet-section" aria-labelledby="shop-heading">
      <h2 id="shop-heading">Tienda de Ardy</h2>
      <NutShop :token="token" :avatar="avatar" :shop-revision="shopRevision"
        @expired="emit('expired')" @unlocked="unlock" @try-on="tryOn" />
      <article v-for="item in items" :key="item.id" class="tile wallet-conversion">
        <div>
          <h3>{{ item.name }}</h3>
          <p>{{ item.owned ? 'En tu armario' : `${item.price} Ardi Coins` }}<template v-if="item.rarity">
            · {{ rarityLabels[item.rarity] }}</template></p>
        </div>
        <button v-if="item.owned" class="button secondary" type="button" :disabled="busy || !!purchasing"
          @click="avatar[item.slot] = item.value">Probar</button>
        <button v-else-if="confirmItem?.id !== item.id" class="button secondary" type="button" :disabled="busy || !!purchasing"
          @click="confirmItem = item">Comprar</button>
        <div v-else class="workshop-actions">
          <button class="button primary" type="button" :disabled="!!purchasing" @click="buy(item)">Confirmar {{ item.price }} Coins</button>
          <button class="button quiet" type="button" :disabled="!!purchasing" @click="confirmItem = undefined">Cancelar</button>
        </div>
      </article>
    </section>
  </section>
</template>
