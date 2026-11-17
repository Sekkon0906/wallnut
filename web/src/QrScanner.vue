<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{
  parse: (value: string) => string | undefined
  instruction: string
  mismatch: string
}>()
const emit = defineEmits<{ code: [value: string]; close: [] }>()
const preview = ref<HTMLVideoElement>()
const error = ref('')
const starting = ref(false)
const reading = ref(false)
let stream: MediaStream | undefined
let frame = 0
let closed = false

function stop() {
  cancelAnimationFrame(frame)
  stream?.getTracks().forEach((track) => track.stop())
  stream = undefined
  if (preview.value) preview.value.srcObject = null
  reading.value = false
}

function stopWhenHidden() {
  if (document.hidden && reading.value) {
    stop()
    error.value = 'La cámara se cerró al cambiar de pantalla.'
  }
}

async function start() {
  const video = preview.value
  if (starting.value || reading.value || !video) return
  error.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    error.value = 'Este navegador no puede abrir la cámara. Ingresa el código manualmente.'
    return
  }
  starting.value = true
  try {
    const { default: decode } = await import('jsqr')
    if (closed) return
    const camera = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 720 } },
      audio: false,
    })
    if (closed || document.hidden) {
      camera.getTracks().forEach((track) => track.stop())
      return
    }
    stream = camera
    video.srcObject = stream
    await video.play()
    if (closed || !stream) return
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d', { willReadFrequently: true })
    if (!context) throw new Error('Camera frame is unavailable')

    reading.value = true
    let lastRead = 0
    function scan(now: number) {
      if (!video || !context || !stream || closed) return
      if (now - lastRead >= 125 && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && video.videoWidth) {
        lastRead = now
        const scale = Math.min(1, 480 / Math.max(video.videoWidth, video.videoHeight))
        const width = Math.max(1, Math.round(video.videoWidth * scale))
        const height = Math.max(1, Math.round(video.videoHeight * scale))
        if (canvas.width !== width || canvas.height !== height) {
          canvas.width = width
          canvas.height = height
        }
        context.drawImage(video, 0, 0, width, height)
        const pixels = context.getImageData(0, 0, width, height)
        const result = decode(pixels.data, width, height, { inversionAttempts: 'dontInvert' })
        if (result) {
          const code = props.parse(result.data)
          if (code) {
            stop()
            emit('code', code)
            return
          }
          error.value = props.mismatch
        }
      }
      frame = requestAnimationFrame(scan)
    }
    frame = requestAnimationFrame(scan)
  } catch {
    stop()
    error.value = 'No pudimos abrir la cámara. Revisa sus permisos o ingresa el código manualmente.'
  } finally {
    starting.value = false
  }
}

onMounted(() => {
  document.addEventListener('visibilitychange', stopWhenHidden)
  void start()
})
onBeforeUnmount(() => {
  closed = true
  document.removeEventListener('visibilitychange', stopWhenHidden)
  stop()
})
</script>

<template>
  <div class="scanner">
    <video v-show="starting || reading" ref="preview" autoplay muted playsinline aria-label="Vista de la cámara"></video>
    <p v-if="starting" role="status">Abriendo la cámara…</p>
    <p v-if="reading">{{ instruction }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="workshop-actions">
      <button v-if="!reading && !starting" class="button secondary" type="button" @click="start">Reintentar</button>
      <button class="button quiet" type="button" @click="emit('close')">Usar código manual</button>
    </div>
  </div>
</template>
