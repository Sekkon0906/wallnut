import { ConnectionMonitor } from './connectivity.js'

export class RequestError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
    this.name = 'RequestError'
  }
}

export type RequestOptions = {
  token?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: object | FormData
}

type TransportSettings = {
  fetcher?: typeof fetch
  timeoutMs?: number
  uploadTimeoutMs?: number
}

export function createTransport(origin: string, monitor: ConnectionMonitor, settings: TransportSettings = {}) {
  const fetcher = settings.fetcher ?? fetch
  return async function request<T>(path: string, options: RequestOptions, accept: string,
                                    read: (response: Response) => Promise<T>): Promise<T> {
    const headers: Record<string, string> = { Accept: accept }
    if (options.token) headers.Authorization = `Bearer ${options.token}`
    let body: BodyInit | undefined
    if (options.data instanceof FormData) body = options.data
    else if (options.data) {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(options.data)
    }
    const requestId = monitor.begin()
    const controller = new AbortController()
    const duration = body instanceof FormData ? (settings.uploadTimeoutMs ?? 60000) : (settings.timeoutMs ?? 15000)
    const timeout = setTimeout(() => controller.abort(), duration)
    try {
      const response = await fetcher(`${origin}/v1${path}`, {
        method: options.method ?? 'GET', headers, body, cache: 'no-store', signal: controller.signal,
      })
      if (!response.ok) {
        const result = await response.json().catch(() => null)
        if (response.status >= 500 && typeof result?.detail !== 'string') monitor.failed(requestId)
        else monitor.received(requestId)
        const detail = typeof result?.detail === 'string' ? result.detail
          : response.status >= 500
            ? 'Wallnut no pudo completar la respuesta. Consulta el resultado antes de repetir la operación.'
            : 'Revisa los datos y vuelve a intentarlo.'
        throw new RequestError(detail, response.status)
      }
      const result = await read(response)
      monitor.received(requestId)
      return result
    } catch (error) {
      if (!(error instanceof RequestError)) monitor.failed(requestId)
      throw error
    } finally {
      clearTimeout(timeout)
    }
  }
}
