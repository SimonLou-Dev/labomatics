import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useA11yStore = defineStore('a11y', () => {
  const dyslexiaMode = ref<boolean>(localStorage.getItem('a11y_dyslexia') === 'true')
  const highContrast = ref<boolean>(localStorage.getItem('a11y_high_contrast') === 'true')
  const largeText = ref<boolean>(localStorage.getItem('a11y_large_text') === 'true')

  const applyDyslexiaMode = (enabled: boolean) => {
    const html = document.documentElement
    if (enabled) {
      html.classList.add('dyslexia-mode')
    } else {
      html.classList.remove('dyslexia-mode')
    }
    localStorage.setItem('a11y_dyslexia', String(enabled))
  }

  const applyHighContrast = (enabled: boolean) => {
    const html = document.documentElement
    if (enabled) {
      html.classList.add('high-contrast')
    } else {
      html.classList.remove('high-contrast')
    }
    localStorage.setItem('a11y_high_contrast', String(enabled))
  }

  const applyLargeText = (enabled: boolean) => {
    const html = document.documentElement
    if (enabled) {
      html.classList.add('large-text')
    } else {
      html.classList.remove('large-text')
    }
    localStorage.setItem('a11y_large_text', String(enabled))
  }

  // Apply saved preferences on init
  watch(
    () => dyslexiaMode.value,
    (value) => applyDyslexiaMode(value),
    { immediate: true }
  )

  watch(
    () => highContrast.value,
    (value) => applyHighContrast(value),
    { immediate: true }
  )

  watch(
    () => largeText.value,
    (value) => applyLargeText(value),
    { immediate: true }
  )

  return {
    dyslexiaMode,
    highContrast,
    largeText,
    applyDyslexiaMode,
    applyHighContrast,
    applyLargeText,
  }
})
