import { test } from 'node:test'
import assert from 'node:assert/strict'
import { SessionStore, tabSessionKey, rememberedSessionKey } from '../.test-build/sessionStorage.js'

function storage() {
  const values = new Map()
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
}

test('la sesión por pestaña conserva compatibilidad y no se recuerda sin elegirlo', () => {
  const tab = storage(), device = storage()
  tab.setItem(tabSessionKey, 'sesion-anterior')
  const store = new SessionStore(() => tab, () => device)
  assert.deepEqual(store.read(), { token: 'sesion-anterior', remembered: false })
  assert.equal(store.saveLogin('sesion-nueva', false), false)
  assert.equal(store.read().token, 'sesion-nueva')
  assert.deepEqual(new SessionStore(() => storage(), () => device).read(), { token: '', remembered: false })
})

test('la elección permite recuperar la credencial en otra apertura y cerrarla de ambos almacenes', () => {
  const tab = storage(), device = storage()
  const store = new SessionStore(() => tab, () => device)
  assert.equal(store.saveLogin('sesion-elegida', true), true)
  const nextTab = storage()
  const reopened = new SessionStore(() => nextTab, () => device)
  assert.deepEqual(reopened.read(), { token: 'sesion-elegida', remembered: true })
  reopened.cacheInTab('sesion-elegida')
  reopened.clear('sesion-elegida')
  assert.equal(nextTab.getItem(tabSessionKey), null)
  assert.equal(device.getItem(rememberedSessionKey), null)
})

test('cerrar una sesión anterior no elimina la cuenta nueva recordada en otra pestaña', () => {
  const tab = storage(), device = storage()
  tab.setItem(tabSessionKey, 'cuenta-anterior')
  device.setItem(rememberedSessionKey, 'cuenta-nueva')
  const store = new SessionStore(() => tab, () => device)
  store.clear('cuenta-anterior')
  assert.equal(tab.getItem(tabSessionKey), null)
  assert.equal(device.getItem(rememberedSessionKey), 'cuenta-nueva')
})

test('recuperar la pestaña no sustituye la preferencia de otra cuenta del dispositivo', () => {
  const tab = storage(), device = storage()
  device.setItem(rememberedSessionKey, 'otra-cuenta')
  const store = new SessionStore(() => tab, () => device)
  store.cacheInTab('cuenta-de-esta-pestana')
  assert.deepEqual(store.read(), { token: 'cuenta-de-esta-pestana', remembered: false })
  assert.equal(device.getItem(rememberedSessionKey), 'otra-cuenta')
})

test('un inicio nuevo sin retención retira la credencial que antes se recordaba', () => {
  const tab = storage(), device = storage()
  device.setItem(rememberedSessionKey, 'sesion-recordada-anterior')
  const store = new SessionStore(() => tab, () => device)
  store.saveLogin('nuevo-inicio', false)
  assert.equal(device.getItem(rememberedSessionKey), null)
  assert.deepEqual(store.read(), { token: 'nuevo-inicio', remembered: false })
})

test('las restricciones de almacenamiento no impiden mantener la cuenta activa en memoria', () => {
  const blocked = () => { throw new DOMException('Almacenamiento restringido', 'SecurityError') }
  const store = new SessionStore(blocked, blocked)
  assert.deepEqual(store.read(), { token: '', remembered: false })
  assert.equal(store.saveLogin('credencial-ficticia', true), false)
  assert.doesNotThrow(() => store.clear('credencial-ficticia'))
})
