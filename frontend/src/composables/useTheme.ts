import { computed, ref, onMounted } from 'vue'

const isDark = ref(false)
const isDyslexia = ref(false)

export const useTheme = () => {
  onMounted(() => {
    initTheme()
    initDyslexia()
  })

  const initTheme = () => {
    const html = document.documentElement
    const saved = localStorage.getItem('theme')

    if (saved === 'dark') {
      html.classList.add('dark')
      isDark.value = true
    } else if (saved === 'light') {
      html.classList.remove('dark')
      isDark.value = false
    } else {
      // Utiliser la préférence système
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        html.classList.add('dark')
        isDark.value = true
      } else {
        html.classList.remove('dark')
        isDark.value = false
      }
    }
  }

  const initDyslexia = () => {
    const html = document.documentElement
    const saved = localStorage.getItem('dyslexia')

    if (saved === 'true') {
      html.classList.add('dyslexia-mode')
      isDyslexia.value = true
    } else {
      html.classList.remove('dyslexia-mode')
      isDyslexia.value = false
    }
  }

  const toggleTheme = () => {
    const html = document.documentElement
    if (html.classList.contains('dark')) {
      html.classList.remove('dark')
      isDark.value = false
      localStorage.setItem('theme', 'light')
    } else {
      html.classList.add('dark')
      isDark.value = true
      localStorage.setItem('theme', 'dark')
    }
  }

  const toggleDyslexia = () => {
    const html = document.documentElement
    if (html.classList.contains('dyslexia-mode')) {
      html.classList.remove('dyslexia-mode')
      isDyslexia.value = false
      localStorage.setItem('dyslexia', 'false')
    } else {
      html.classList.add('dyslexia-mode')
      isDyslexia.value = true
      localStorage.setItem('dyslexia', 'true')
    }
  }

  return {
    isDark: computed(() => isDark.value),
    isDyslexia: computed(() => isDyslexia.value),
    toggleTheme,
    toggleDyslexia,
    initTheme,
    initDyslexia,
  }
}
