import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ConnectionMonitor } from '../.test-build/connectivity.js'

test('una respuesta antigua no sustituye el resultado de una consulta más reciente', () => {
  const monitor = new ConnectionMonitor()
  const states = []
  const unsubscribe = monitor.subscribe(value => states.push(value))
  const older = monitor.begin()
  const newer = monitor.begin()
  monitor.failed(newer)
  monitor.received(older)
  assert.equal(monitor.state.reachable, false)
  const failedEarlier = monitor.begin()
  const successfulLater = monitor.begin()
  monitor.received(successfulLater)
  monitor.failed(failedEarlier)
  assert.equal(monitor.state.reachable, true)
  assert.equal(monitor.state.recovered, true)
  monitor.dismissRecovery()
  assert.equal(monitor.state.recovered, false)
  assert.equal(states.length, 4)
  unsubscribe()
  monitor.failed(monitor.begin())
  assert.equal(states.length, 4)
})

test('volver a la red no confirma el servicio hasta recibir una respuesta nueva', () => {
  const monitor = new ConnectionMonitor()
  const inFlight = monitor.begin()
  monitor.setOnline(false)
  monitor.received(inFlight)
  assert.deepEqual(monitor.state, { online: false, reachable: false, recovered: false })
  const whileOffline = monitor.begin()
  monitor.setOnline(true)
  monitor.received(whileOffline)
  assert.deepEqual(monitor.state, { online: true, reachable: false, recovered: false })
  monitor.received(monitor.begin())
  assert.deepEqual(monitor.state, { online: true, reachable: true, recovered: true })
  assert.ok(Object.isFrozen(monitor.state))
})
