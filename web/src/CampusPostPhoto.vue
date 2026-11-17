<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { apiPhoto, RequestError } from './client'

const props = defineProps<{ token: string; postId: string; version: string | null }>()
const emit = defineEmits<{ expired: [] }>()
const container = ref<HTMLElement>()
const nearby = ref(false)
const attempt = ref(0)
const url = ref('')
const failed = ref(false)
let observer: IntersectionObserver | undefined

onMounted(() => {
  if (!container.value || typeof IntersectionObserver === 'undefined') {
    nearby.value = true
    return
  }
  observer = new IntersectionObserver(entries => {
    if (!entries.some(entry => entry.isIntersecting)) return
    nearby.value = true
    observer?.disconnect()
  }, { rootMargin: '200px' })
  observer.observe(container.value)
})

onBeforeUnmount(() => observer?.disconnect())

watch([nearby, attempt, () => props.token, () => props.postId, () => props.version],
  async ([isNearby], _, onCleanup) => {
    if (!isNearby) return
    let current = true
    let photoUrl = ''
    onCleanup(() => {
      current = false
      if (photoUrl) URL.revokeObjectURL(photoUrl)
    })
    url.value = ''
    failed.value = false
    try {
      const photo = await apiPhoto(`/posts/${props.postId}/photo`, props.token)
      if (!current) return
      photoUrl = URL.createObjectURL(photo)
      url.value = photoUrl
    } catch (error) {
      if (!current) return
      if (error instanceof RequestError && error.status === 401) emit('expired')
      else failed.value = true
    }
  },
)
</script>

<template>
  <figure ref="container" class="post-photo">
    <img v-if="url" :src="url" alt="Foto adjunta a la publicación" decoding="async" />
    <button v-else-if="failed" class="button quiet" type="button" @click="attempt++">Volver a cargar la foto</button>
    <p v-else class="state-note" :role="nearby ? 'status' : undefined">{{ nearby ? 'Cargando foto…' : 'Foto adjunta' }}</p>
  </figure>
</template>

<style scoped>
.post-photo {
  display: grid;
  justify-items: center;
  align-items: center;
  min-height: 7rem;
  margin: 0;
  overflow: hidden;
  border-radius: .8rem;
  background: #f0f4f9;
}
.post-photo img { display: block; max-width: 100%; max-height: 30rem; object-fit: contain; }
</style>
