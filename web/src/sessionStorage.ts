type StorageLike = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
type StorageAccess = () => StorageLike | null
export const tabSessionKey = 'wallnut.session'
export const rememberedSessionKey = 'wallnut.remembered-session'

export class SessionStore {
  private tab: StorageAccess
  private device: StorageAccess
  constructor(tab: StorageAccess, device: StorageAccess) {
    this.tab = tab
    this.device = device
  }

  private get(access: StorageAccess, key: string) {
    try { return access()?.getItem(key) ?? '' } catch { return '' }
  }

  private put(access: StorageAccess, key: string, token: string) {
    try {
      const storage = access()
      storage?.setItem(key, token)
      return storage?.getItem(key) === token
    } catch { return false }
  }

  private remove(access: StorageAccess, key: string) {
    try { access()?.removeItem(key) } catch { /* La cuenta activa puede seguir en memoria. */ }
  }

  read() {
    const tab = this.get(this.tab, tabSessionKey)
    const device = this.get(this.device, rememberedSessionKey)
    return { token: tab || device, remembered: !!device && (!tab || tab === device) }
  }

  cacheInTab(token: string) { return this.put(this.tab, tabSessionKey, token) }

  saveLogin(token: string, remember: boolean) {
    this.cacheInTab(token)
    this.remove(this.device, rememberedSessionKey)
    return remember && this.put(this.device, rememberedSessionKey, token)
  }

  clear(token: string) {
    if (!token) return
    if (this.get(this.tab, tabSessionKey) === token) this.remove(this.tab, tabSessionKey)
    if (this.get(this.device, rememberedSessionKey) === token) this.remove(this.device, rememberedSessionKey)
  }
}
