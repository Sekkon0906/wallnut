<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, errorText, RequestError } from './client'
import type { ArdyProfile, CampusProfile } from './ardy'
import CampusProfileCard from './CampusProfileCard.vue'

type Settings = { bio: string; visible: boolean; show_career: boolean }
const props = defineProps<{ token: string; displayName: string; ardy: ArdyProfile }>()
const emit = defineEmits<{ expired: [] }>()
const saved = ref<Settings>()
const draft = ref<Settings>({ bio: '', visible: false, show_career: false })
const busy = ref(false)
const problem = ref('')
const notice = ref('')
const changed = computed(() => !!saved.value && (
  draft.value.bio.trim() !== saved.value.bio
  || draft.value.visible !== saved.value.visible
  || draft.value.show_career !== saved.value.show_career
))
const preview = computed<CampusProfile>(() => ({
  display_name: props.displayName,
  avatar: props.ardy.avatar,
  bio: draft.value.bio.trim(),
  career: draft.value.show_career ? props.ardy.career : null,
}))

async function update(save = false) {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  notice.value = ''
  try {
    const settings = await api<Settings>('/my-campus-profile', save
      ? { token: props.token, method: 'PUT', data: draft.value }
      : { token: props.token })
    saved.value = settings
    draft.value = { ...settings }
    if (save) notice.value = settings.visible ? 'Tu perfil es visible para la comunidad.' : 'Guardaste tu perfil privado.'
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

onMounted(() => update())
</script>

<template>
  <section class="campus-profile-editor" aria-labelledby="campus-profile-heading">
    <h2 id="campus-profile-heading">Mi perfil del campus</h2>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="busy && !saved" role="status">Cargando tu perfil…</p>
    <button v-if="problem && !saved" class="button secondary" type="button" @click="update()">Reintentar</button>
    <div v-if="saved" class="campus-profile-layout">
      <form class="tile campus-profile-form" @submit.prevent="update(true)">
        <fieldset class="form-stack" :disabled="busy">
          <label>Presentación
            <textarea v-model="draft.bio" rows="3" maxlength="280" placeholder="Escribe algo sobre ti"></textarea>
          </label>
          <label class="check-label"><input v-model="draft.visible" type="checkbox" /> Mostrar mi perfil en el campus</label>
          <label class="check-label"><input v-model="draft.show_career" type="checkbox" /> Mostrar mi carrera en el perfil</label>
          <p>Si haces visible tu perfil, la comunidad podrá abrirlo desde los eventos que organices.</p>
          <button class="button primary" type="submit" :disabled="!changed">Guardar perfil</button>
        </fieldset>
      </form>
      <aside class="tile campus-profile-preview" aria-label="Vista previa de tu perfil">
        <p>Vista previa</p>
        <CampusProfileCard :profile="preview" />
      </aside>
    </div>
  </section>
</template>

<style scoped>
.campus-profile-editor { margin-top: 1.5rem; }
.campus-profile-editor h2 { margin-bottom: .65rem; font-size: 1.2rem; }
.campus-profile-layout { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 1rem; }
.campus-profile-form, .campus-profile-preview { padding: 1rem; }
.campus-profile-form fieldset { border: 0; padding: 0; min-width: 0; margin: 0; }
.campus-profile-preview > p { text-align: center; font-weight: 650; }
@media (max-width: 650px) { .campus-profile-layout { grid-template-columns: 1fr; } }
</style>
