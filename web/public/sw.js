const offlineCache = 'wallnut-offline-v2'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(offlineCache).then((cache) => cache.addAll([
    '/offline.html',
    '/icon-192.png',
  ])))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((names) => Promise.all(
    names.filter((name) => name.startsWith('wallnut-offline-') && name !== offlineCache)
      .map((name) => caches.delete(name)),
  )))
})

self.addEventListener('fetch', (event) => {
  if (event.request.mode !== 'navigate') return
  const url = new URL(event.request.url)
  if (url.origin !== self.location.origin || url.pathname !== '/') return
  event.respondWith(fetch(event.request).catch(() => caches.match('/offline.html')))
})
