<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  DirectionalLight, Group, HemisphereLight, Mesh, MeshBasicMaterial,
  PerspectiveCamera, CircleGeometry, Scene, Vector3, WebGLRenderer,
} from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { ChevronLeft, ChevronRight, RotateCcw } from '@lucide/vue'
import type { Avatar } from './ardy'
import { buildArdy, disposeArdy } from './ardyModel'

const props = defineProps<{ avatar: Avatar }>()
const emit = defineEmits<{ unavailable: [] }>()
const canvas = ref<HTMLCanvasElement>()
const initialPosition = new Vector3(2.6, 2.2, 5.6)
const target = new Vector3(.24, 1.4, -.14)
let scene: Scene | undefined
let camera: PerspectiveCamera | undefined
let renderer: WebGLRenderer | undefined
let controls: OrbitControls | undefined
let observer: ResizeObserver | undefined
let avatarModel: Group | undefined
let ground: Mesh<CircleGeometry, MeshBasicMaterial> | undefined

function render() {
  if (renderer && scene && camera) renderer.render(scene, camera)
}

function fit() {
  if (!canvas.value || !renderer || !camera) return
  const { width, height } = canvas.value.getBoundingClientRect()
  if (!width || !height) return
  camera.aspect = width / height
  camera.fov = 36 / Math.min(camera.aspect, 1)
  camera.updateProjectionMatrix()
  renderer.setSize(width, height, false)
  render()
}

function updateAvatar() {
  if (!scene) return
  if (avatarModel) {
    scene.remove(avatarModel)
    disposeArdy(avatarModel)
  }
  avatarModel = buildArdy(props.avatar)
  scene.add(avatarModel)
  render()
}

function rotate(step: number) {
  if (!camera || !controls) return
  const offset = camera.position.clone().sub(controls.target)
  offset.applyAxisAngle(camera.up, step * Math.PI / 6)
  camera.position.copy(controls.target).add(offset)
  controls.update()
}

function center() {
  if (!camera || !controls) return
  camera.position.copy(initialPosition)
  controls.update()
}

watch(() => props.avatar, updateAvatar, { deep: true })

onMounted(() => {
  const surface = canvas.value
  if (!surface) return
  try {
    const context = surface.getContext('webgl2', { alpha: true, antialias: true, powerPreference: 'low-power' })
    if (!context) {
      emit('unavailable')
      return
    }
    renderer = new WebGLRenderer({ canvas: surface, context, alpha: true, antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
    camera = new PerspectiveCamera(36, 1, .1, 20)
    camera.position.copy(initialPosition)
    controls = new OrbitControls(camera, surface)
    controls.target.copy(target)
    controls.enablePan = false
    controls.enableZoom = false
    controls.minPolarAngle = Math.PI / 4
    controls.maxPolarAngle = Math.PI / 2
    controls.update()

    scene = new Scene()
    const key = new DirectionalLight('#fff3db', 2.4)
    key.position.set(-2, 5, 4)
    const fill = new DirectionalLight('#c3dbff', 1.3)
    fill.position.set(3, 3, -4)
    scene.add(key, fill, new HemisphereLight('#f2f6ff', '#ac93a0', 2))
    ground = new Mesh(new CircleGeometry(1.02, 48), new MeshBasicMaterial({ color: '#a8c5ea' }))
    ground.rotation.x = -Math.PI / 2
    ground.position.set(.15, -.006, -.15)
    scene.add(ground)
    updateAvatar()
    controls.addEventListener('change', render)
    observer = new ResizeObserver(fit)
    observer.observe(surface)
    fit()
  } catch {
    emit('unavailable')
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  controls?.removeEventListener('change', render)
  controls?.dispose()
  if (avatarModel) disposeArdy(avatarModel)
  ground?.geometry.dispose()
  ground?.material.dispose()
  renderer?.dispose()
})
</script>

<template>
  <div class="model-preview">
    <canvas ref="canvas" role="img" aria-label="Vista 3D de tu Ardy" @webglcontextlost="emit('unavailable')"></canvas>
    <div class="model-controls" role="group" aria-label="Girar tu Ardy">
      <button class="button secondary" type="button" aria-label="Girar a la izquierda" @click="rotate(-1)">
        <ChevronLeft :size="20" aria-hidden="true" />
      </button>
      <button class="button secondary" type="button" @click="center">
        <RotateCcw :size="16" aria-hidden="true" /> Centrar
      </button>
      <button class="button secondary" type="button" aria-label="Girar a la derecha" @click="rotate(1)">
        <ChevronRight :size="20" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.model-preview canvas { display: block; width: 100%; height: clamp(245px, 45vw, 360px); cursor: grab; }
.model-preview canvas:active { cursor: grabbing; }
.model-controls { display: flex; flex-wrap: wrap; justify-content: center; gap: .4rem; margin: .25rem 0 .75rem; }
.model-controls .button { display: inline-flex; align-items: center; gap: .4rem; min-height: 44px; }
</style>
