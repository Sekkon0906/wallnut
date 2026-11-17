<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download } from '@lucide/vue'
import { api, errorText, RequestError } from './client'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ expired: [] }>()
const funnel = [
  ['workshop_enrollments', 'Inscripciones'], ['attendances', 'Asistencias'],
  ['evidence_delivered', 'Evidencias entregadas'], ['evidence_approved', 'Evidencias aprobadas'],
] as const
const groups = [
  { name: 'Talleres', columns: [['workshops', 'Talleres finalizados'], ...funnel] },
  { name: 'Eventos', columns: [['events', 'Eventos realizados'], ['event_enrollments', 'Inscripciones']] },
  { name: 'Billetera y armario', columns: [
    ['points_awards', 'Premios de Points'], ['coin_goal_awards', 'Premios de Coins'],
    ['coin_conversions', 'Conversiones a Points'], ['coin_payments', 'Pagos con Coins'],
    ['approved_redemptions', 'Canjes académicos aprobados'], ['item_purchases', 'Prendas compradas'],
    ['nuts_purchased', 'Nueces compradas'], ['nuts_opened', 'Nueces abiertas'],
  ] },
] as const

type Metric = typeof groups[number]['columns'][number][0]
type PilotWeek = { week: string } & Record<Metric, number>
interface PilotReport { generated_at: string; through: string; time_zone: string; weeks: PilotWeek[] }

const weeks = ref(4)
const through = ref('')
const report = ref<PilotReport>()
const busy = ref(false)
const problem = ref('')
const dateLabel = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'UTC' })
const number = new Intl.NumberFormat('es-CO')
const totals = computed(() => funnel.map(([key, label]) => ({
  label, count: report.value?.weeks.reduce((sum, row) => sum + row[key], 0) ?? 0,
})))

function formatDate(date: string) {
  return dateLabel.format(new Date(`${date}T00:00:00Z`))
}

async function load() {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  const parameters = new URLSearchParams({ weeks: String(weeks.value) })
  if (through.value) parameters.set('through', through.value)
  try {
    report.value = await api<PilotReport>(`/admin/pilot-metrics?${parameters}`, { token: props.token })
  } catch (error) {
    if (error instanceof RequestError && error.status === 401) emit('expired')
    else problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

function download() {
  const data = report.value
  if (!data) return
  const columns = groups.flatMap(group => group.columns.map(([key, name]) => ({ key, label: `${group.name} · ${name}` })))
  const rows = [
    ['Semana (lunes)', 'Fecha de corte', 'Generado el', 'Zona horaria', ...columns.map(column => column.label)],
    ...data.weeks.map(row => [row.week, data.through, data.generated_at, data.time_zone, ...columns.map(column => row[column.key])]),
  ]
  const csv = rows.map(row => row.map(value => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `wallnut-piloto-${data.through}.csv`
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

onMounted(load)
</script>

<template>
  <section class="pilot-report" aria-labelledby="pilot-report-title">
    <header class="report-header">
      <div>
        <h1 id="pilot-report-title">Evaluación del piloto</h1>
        <p>Participación semanal en Wallnut, en hora de Colombia.</p>
      </div>
      <button v-if="report" class="button secondary download" type="button" :disabled="busy" @click="download">
        <Download :size="18" aria-hidden="true" /> Descargar CSV
      </button>
    </header>

    <form class="tile form-stack report-filters" @submit.prevent="load">
      <label>Periodo
        <select v-model.number="weeks" :disabled="busy">
          <option :value="4">4 semanas</option>
          <option :value="8">8 semanas</option>
          <option :value="12">12 semanas</option>
        </select>
      </label>
      <label>Fecha de corte (opcional)
        <input v-model="through" type="date" :disabled="busy" min="2000-01-01" :max="report?.generated_at.slice(0, 10)" />
      </label>
      <button class="button primary" :disabled="busy">Consultar</button>
    </form>
    <p v-if="busy" role="status">Cargando el informe…</p>
    <p v-if="problem" class="error" role="alert">{{ problem }}</p>

    <template v-if="report">
      <section class="tile funnel" aria-labelledby="workshop-funnel-title">
        <div>
          <p class="report-period">{{ formatDate(report.weeks[report.weeks.length - 1]!.week) }} – {{ formatDate(report.through) }}</p>
          <h2 id="workshop-funnel-title">Participación en talleres</h2>
          <p>Incluye talleres finalizados al corte y el estado actual de sus evidencias.</p>
        </div>
        <dl>
          <div v-for="entry in totals" :key="entry.label">
            <dt>{{ entry.label }}</dt>
            <dd>{{ number.format(entry.count) }}</dd>
            <div class="funnel-track" aria-hidden="true">
              <span :style="{ width: `${entry.count * 100 / (totals[0]?.count || 1)}%` }"></span>
            </div>
          </div>
        </dl>
      </section>

      <section class="weekly" aria-label="Detalle por semana">
        <details v-for="group in groups" :key="group.name" class="tile metrics-table" :open="group.name === 'Talleres'">
          <summary>{{ group.name }} por semana</summary>
          <p v-if="group.name === 'Eventos'">Incluye eventos con fecha de inicio cumplida y sus inscripciones.</p>
          <p v-if="group.name === 'Billetera y armario'">Las nueces se agrupan por semana de compra. El informe muestra cuántas ya se abrieron.</p>
          <div class="table-scroll" :aria-label="`${group.name} por semana`" role="region" tabindex="0">
            <table>
              <thead>
                <tr><th scope="col">Semana del</th><th v-for="[, label] in group.columns" :key="label" scope="col">{{ label }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in report.weeks" :key="row.week">
                  <th scope="row">{{ formatDate(row.week) }}</th>
                  <td v-for="[key] in group.columns" :key="key">{{ number.format(row[key]) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </section>
    </template>
  </section>
</template>

<style scoped>
.pilot-report, .weekly { display: grid; gap: 1rem; }
.report-header { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: .75rem; }
.report-header p, .funnel p, .metrics-table p { margin: .3rem 0 0; color: var(--muted); }
.download { display: inline-flex; align-items: center; gap: .5rem; }
.report-filters { display: flex; flex-wrap: wrap; align-items: flex-end; gap: .8rem; }
.report-filters label { flex: 1 1 175px; display: grid; gap: .3rem; }
.report-filters button { min-height: 44px; }
.funnel { display: grid; gap: .75rem; }
.funnel .report-period { margin: 0 0 .4rem; color: var(--blue); font-weight: 650; }
.funnel dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; margin: .5rem 0 0; }
.funnel dl > div { display: grid; align-content: end; gap: .2rem; }
.funnel dt { color: var(--muted); font-size: .86rem; }
.funnel dd { margin: 0; font-size: 1.65rem; font-weight: 760; }
.funnel-track { height: .38rem; border-radius: 2rem; background: #dfebfc; overflow: hidden; }
.funnel-track span { display: block; height: 100%; border-radius: inherit; background: var(--blue); }
.metrics-table { min-width: 0; }
.metrics-table summary { padding: .25rem 0; cursor: pointer; font-weight: 740; }
.table-scroll { overflow-x: auto; margin-top: .55rem; }
.table-scroll table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.table-scroll th, .table-scroll td { padding: .65rem; text-align: right; border-top: 1px solid var(--line); }
.table-scroll thead { background: var(--light); }
.table-scroll th:first-child { min-width: 113px; text-align: left; }
</style>
