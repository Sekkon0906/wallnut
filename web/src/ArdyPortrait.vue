<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { drawArdy, type Avatar } from './ardy'

const props = defineProps<{ avatar: Avatar; small?: boolean }>()
const canvas = ref<HTMLCanvasElement>()
watchEffect(() => {
  if (canvas.value) drawArdy(canvas.value, props.avatar)
})
</script>

<template>
  <canvas ref="canvas" :width="small ? 96 : 400" :height="small ? 86 : 360"
    :class="['ardy-portrait', { 'ardy-small': small }]" aria-hidden="true"></canvas>
</template>
