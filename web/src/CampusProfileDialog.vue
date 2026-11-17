<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { X } from '@lucide/vue'
import { api, errorText, RequestError } from './client'
import type { CampusProfile } from './ardy'
import CampusProfileCard from './CampusProfileCard.vue'

const props = defineProps<{ token: string; studentId: string }>()
const emit = defineEmits<{ expired: []; close: [] }>()
const dialog = ref<HTMLDialogElement>()
const data = ref<CampusProfile>()
const busy = ref(false)
const unavailable = ref(false)
const problem = ref('')

async function load() {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  try {
    data.value = await api<CampusProfile>(`/campus-profiles/${props.studentId}`, { token: props.token })
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else {
      unavailable.value = error instanceof RequestError && error.status === 404
      problem.value = errorText(error)
    }
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  dialog.value?.showModal()
  void load()
})
</script>

<template>
  <dialog ref="dialog" class="campus-profile-dialog" aria-labelledby="campus-profile-dialog-title" @close="emit('close')">
    <header>
      <h2 id="campus-profile-dialog-title">Perfil del campus</h2>
      <button class="button quiet" type="button" aria-label="Cerrar perfil" @click="dialog?.close()">
        <X :size="20" aria-hidden="true" />
      </button>
    </header>
    <p v-if="busy" role="status">Cargando perfil…</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <button v-if="problem && !unavailable" class="button secondary" type="button" @click="load">Reintentar</button>
    <CampusProfileCard v-if="data" :profile="data" />
  </dialog>
</template>

<style scoped>
.campus-profile-dialog { width: min(calc(100% - 1.5rem), 27rem); color: var(--ink); border: 1px solid var(--line); border-radius: 1.2rem; padding: 1rem; }
.campus-profile-dialog::backdrop { background: #13254090; }
.campus-profile-dialog header { display: flex; justify-content: space-between; align-items: center; gap: .5rem; }
.campus-profile-dialog h2 { font-size: 1.15rem; }
</style>
