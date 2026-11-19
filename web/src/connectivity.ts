export interface ConnectionState {
  readonly online: boolean
  readonly reachable: boolean | null
  readonly recovered: boolean
}

export class ConnectionMonitor {
  private sequence = 0
  private observed = 0
  private current: Readonly<ConnectionState>
  private listeners = new Set<(state: Readonly<ConnectionState>) => void>()

  constructor(online = true) {
    this.current = Object.freeze({ online, reachable: online ? null : false, recovered: false })
  }

  get state() { return this.current }

  subscribe(listener: (state: Readonly<ConnectionState>) => void) {
    this.listeners.add(listener)
    listener(this.current)
    return () => { this.listeners.delete(listener) }
  }

  private publish(value: ConnectionState) {
    this.current = Object.freeze(value)
    for (const listener of this.listeners) listener(this.current)
  }

  begin() { return ++this.sequence }

  received(request: number) {
    if (request < this.observed) return
    this.observed = request
    this.publish({ ...this.current, reachable: true,
      recovered: this.current.recovered || this.current.reachable === false })
  }

  failed(request: number) {
    if (request < this.observed) return
    this.observed = request
    this.publish({ ...this.current, reachable: false, recovered: false })
  }

  setOnline(online: boolean) {
    if (online === this.current.online) return
    this.observed = ++this.sequence
    this.publish({ online, reachable: false, recovered: false })
  }

  dismissRecovery() {
    if (this.current.reachable) this.publish({ ...this.current, recovered: false })
  }
}

export const connection = new ConnectionMonitor(typeof navigator === 'undefined' || navigator.onLine)
