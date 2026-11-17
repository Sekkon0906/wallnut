import type { CapacitorConfig } from '@capacitor/cli'

const demoServer = process.env.CAPACITOR_LOCAL_DEMO === 'true'

const config: CapacitorConfig = {
  appId: 'dev.wallnut.campus',
  appName: 'Wallnut',
  webDir: 'dist',
  plugins: {
    SocialLogin: {
      providers: { google: true, apple: false, facebook: false, twitter: false },
      logLevel: 1,
    },
  },
  ...(demoServer ? { server: { url: 'http://localhost:5173', cleartext: true } } : {}),
}

export default config
