<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, errorText, RequestError, type Course } from './client'
import FacultyBudgetView from './FacultyBudgetView.vue'

interface Faculty { id: string; display_name: string; email: string }

const props = defineProps<{ token: string; accountId: string; courses: Course[] }>()
const emit = defineEmits<{ changed: []; expired: [] }>()
const faculty = ref<Faculty[]>([])
const email = ref('')
const member = ref('')
const courseId = ref('')
const course = reactive({ code: '', title: '', term: '', section: '', faculty_id: '' })
const busy = ref(false)
const notice = ref('')
const problem = ref('')
const facultyRevision = ref(0)

async function run(work: () => Promise<void>) {
  if (busy.value) return
  notice.value = ''
  problem.value = ''
  busy.value = true
  try {
    await work()
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

async function loadFaculty() {
  faculty.value = await api<Faculty[]>('/faculty', { token: props.token })
}
onMounted(() => run(loadFaculty))

function enableFaculty() {
  return run(async () => {
    await api('/faculty', { token: props.token, method: 'POST', data: { email: email.value } })
    email.value = ''
    await loadFaculty()
    facultyRevision.value += 1
    notice.value = 'Docente habilitado.'
  })
}

function createCourse() {
  return run(async () => {
    await api('/courses', { token: props.token, method: 'POST', data: course })
    Object.assign(course, { code: '', title: '', term: '', section: '', faculty_id: '' })
    notice.value = 'Grupo creado.'
    emit('changed')
  })
}

function enroll() {
  return run(async () => {
    await api(`/courses/${courseId.value}/students`, {
      token: props.token, method: 'PUT', data: { email: member.value },
    })
    member.value = ''
    notice.value = 'Matrícula confirmada.'
  })
}
</script>

<template>
  <section class="admin-panel">
    <h2>Administración académica</h2>
    <FacultyBudgetView :key="facultyRevision" :token="token" :account-id="accountId" allocate
      @expired="emit('expired')" />
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>
    <div class="admin-grid">
      <form class="tile form-stack" @submit.prevent="enableFaculty">
        <h3>Habilitar docente</h3>
        <label>Correo del docente <input v-model.trim="email" type="email" required /></label>
        <button class="button secondary" :disabled="busy">Asignar rol</button>
      </form>
      <form class="tile form-stack" @submit.prevent="createCourse">
        <h3>Crear grupo</h3>
        <label>Nombre de la materia <input v-model.trim="course.title" maxlength="100" required /></label>
        <div class="form-row">
          <label>Código <input v-model.trim="course.code" maxlength="24" required /></label>
          <label>Periodo <input v-model.trim="course.term" maxlength="24" required /></label>
          <label>Grupo <input v-model.trim="course.section" maxlength="24" required /></label>
        </div>
        <label>Docente
          <select v-model="course.faculty_id" required>
            <option value="" disabled>Selecciona un docente</option>
            <option v-for="teacher in faculty" :key="teacher.id" :value="teacher.id">{{ teacher.display_name }}</option>
          </select>
        </label>
        <button class="button secondary" :disabled="busy">Crear grupo</button>
      </form>
      <form class="tile form-stack" @submit.prevent="enroll">
        <h3>Confirmar matrícula</h3>
        <label>Grupo
          <select v-model="courseId" required>
            <option value="" disabled>Selecciona un grupo</option>
            <option v-for="item in courses" :key="item.id" :value="item.id">{{ item.title }} · {{ item.section }}</option>
          </select>
        </label>
        <label>Correo del estudiante <input v-model.trim="member" type="email" required /></label>
        <button class="button secondary" :disabled="busy">Confirmar matrícula</button>
      </form>
    </div>
  </section>
</template>
