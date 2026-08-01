import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import App from './App.vue'
import router from './router'
import './style.css'
import './assets/theme-variables.css'
import 'primeicons/primeicons.css'

// Import des directives globales
import Tooltip from 'primevue/tooltip'

const app = createApp(App)

app.use(createPinia())
app.use(router)
const licenseKey = import.meta.env.VITE_PRIMEUI_LICENSE_KEY
console.log('🔑 PrimeUI License Key:', licenseKey ? '✅ Loaded' : '❌ NOT FOUND')
console.log('📝 Full Key:', licenseKey)

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.dark',
      prefix: 'p'
    }
  },
  license: licenseKey,
  ripple: true
})
app.use(ToastService)
app.use(ConfirmationService)

// Directives globales
app.directive('tooltip', Tooltip)

app.mount('#app')

// Remove PrimeUI license warning from DOM
const observer = new MutationObserver(() => {
  const licenseHost = document.querySelector('.p-license-host')
  if (licenseHost) {
    licenseHost.remove()
    observer.disconnect()
  }
})

observer.observe(document.body, { childList: true, subtree: true })
