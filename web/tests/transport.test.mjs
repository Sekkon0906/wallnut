import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ConnectionMonitor } from '../.test-build/connectivity.js'
import { createTransport, RequestError } from '../.test-build/transport.js'

const json = response => response.json()

test('un pago guardado con respuesta perdida no se repite y se puede consultar con GET', async () => {
  const monitor = new ConnectionMonitor()
  const calls = []
  let payments = 0
  const request = createTransport('https://wallnut.example.test', monitor, {
    fetcher: async (url, options) => {
      calls.push(options.method)
      if (options.method === 'POST') {
        payments++
        throw new TypeError('Respuesta interrumpida después de guardar')
      }
      return Response.json({ status: payments ? 'paid' : 'pending' })
    },
  })
  await assert.rejects(request('/coin-payments/ficticio/pay', { method: 'POST' }, 'application/json', json), TypeError)
  assert.equal(payments, 1)
  assert.equal(monitor.state.reachable, false)
  const result = await request('/coin-payments/ficticio', {}, 'application/json', json)
  assert.equal(result.status, 'paid')
  assert.deepEqual(calls, ['POST', 'GET'])
  assert.equal(payments, 1)
  assert.equal(monitor.state.recovered, true)
})

test('el vencimiento de una solicitud aborta una sola petición y conserva el resultado incierto', async () => {
  const monitor = new ConnectionMonitor()
  let attempts = 0
  const request = createTransport('', monitor, {
    timeoutMs: 5,
    fetcher: async (url, options) => {
      attempts++
      return await new Promise((resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(new DOMException('Venció la espera', 'AbortError')), { once: true })
      })
    },
  })
  await assert.rejects(request('/ardy-nuts', { method: 'POST', data: { id: 'compra-ficticia' } }, 'application/json', json), { name: 'AbortError' })
  assert.equal(attempts, 1)
  assert.equal(monitor.state.reachable, false)
})

test('una sesión vencida conserva el error 401 y no se confunde con pérdida de conexión', async () => {
  const monitor = new ConnectionMonitor()
  const request = createTransport('', monitor, {
    fetcher: async () => Response.json({ detail: 'La sesión terminó.' }, { status: 401 }),
  })
  await assert.rejects(request('/session', {}, 'application/json', json), error => {
    assert.ok(error instanceof RequestError)
    assert.equal(error.status, 401)
    assert.equal(error.message, 'La sesión terminó.')
    return true
  })
  assert.equal(monitor.state.reachable, true)
  assert.equal(monitor.state.recovered, false)
})

test('un error del servicio sin JSON conserva el código y pide consultar el resultado', async () => {
  const monitor = new ConnectionMonitor()
  let attempts = 0
  const request = createTransport('', monitor, {
    fetcher: async () => { attempts++; return new Response('Servicio temporalmente no disponible', { status: 503 }) },
  })
  await assert.rejects(request('/coin-payments/ficticio/pay', { method: 'POST' }, 'application/json', json), error => {
    assert.ok(error instanceof RequestError)
    assert.equal(error.status, 503)
    assert.match(error.message, /Consulta el resultado/)
    return true
  })
  assert.equal(attempts, 1)
  assert.equal(monitor.state.reachable, false)
})

test('un error específico de acceso conserva el mensaje del servidor y no se presenta como desconexión', async () => {
  const monitor = new ConnectionMonitor()
  const request = createTransport('', monitor, {
    fetcher: async () => Response.json({ detail: 'El acceso institucional aún no está configurado.' }, { status: 503 }),
  })
  await assert.rejects(request('/session', { method: 'POST', data: { credential: 'credencial-ficticia' } }, 'application/json', json), error => {
    assert.equal(error.status, 503)
    assert.equal(error.message, 'El acceso institucional aún no está configurado.')
    return true
  })
  assert.equal(monitor.state.reachable, true)
})

test('subir una foto mantiene FormData, autorización y no permite cachear datos privados', async () => {
  const monitor = new ConnectionMonitor()
  const data = new FormData()
  data.append('reflection', 'Reflexión ficticia')
  data.append('photo', new Blob(['imagen de prueba'], { type: 'image/jpeg' }), 'evidencia.jpg')
  const request = createTransport('https://wallnut.example.test', monitor, {
    fetcher: async (url, options) => {
      assert.equal(url, 'https://wallnut.example.test/v1/workshops/ficticio/evidence')
      assert.equal(options.method, 'POST')
      assert.equal(options.headers.Authorization, 'Bearer sesion-ficticia')
      assert.equal(options.headers['Content-Type'], undefined)
      assert.equal(options.cache, 'no-store')
      assert.equal(options.body, data)
      return Response.json({ status: 'submitted' }, { status: 201 })
    },
  })
  assert.deepEqual(await request('/workshops/ficticio/evidence', { method: 'POST', data, token: 'sesion-ficticia' }, 'application/json', json), { status: 'submitted' })
  assert.equal(JSON.stringify(monitor.state).includes('sesion-ficticia'), false)
  assert.equal(monitor.state.reachable, true)
})

test('una respuesta truncada no se interpreta como operación confirmada', async () => {
  const monitor = new ConnectionMonitor()
  let attempts = 0
  const request = createTransport('', monitor, {
    fetcher: async () => { attempts++; return new Response('{"status":', { status: 200 }) },
  })
  await assert.rejects(request('/coin-payments/ficticio/pay', { method: 'POST' }, 'application/json', json), SyntaxError)
  assert.equal(attempts, 1)
  assert.equal(monitor.state.reachable, false)
})
