import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

function splitHosts(value: string | undefined): string[] {
  if (!value) return []
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

const allowedHosts = Array.from(
  new Set([
    'localhost',
    '127.0.0.1',
    ...splitHosts(process.env.VITE_ALLOWED_HOSTS),
    ...splitHosts(process.env.ALLOWED_HOSTS),
  ]),
)

const devProxyTarget =
  process.env.VITE_DEV_PROXY_TARGET ||
  process.env.DEV_PROXY_TARGET ||
  'http://api:8000'

export default defineConfig({
  plugins: [vue()],

  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts,

    proxy: {
      '/api': {
        target: devProxyTarget,
        changeOrigin: true,
      },
      '/media': {
        target: devProxyTarget,
        changeOrigin: true,
      },
    },
  },

  preview: {
    host: '0.0.0.0',
    port: 4173,
    strictPort: true,
    allowedHosts,
  },
})