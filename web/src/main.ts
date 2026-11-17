import { Capacitor } from '@capacitor/core'
import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')

if (import.meta.env.PROD && !Capacitor.isNativePlatform() && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.warn('Wallnut no pudo preparar la página sin conexión.', error)
    })
  })
}
