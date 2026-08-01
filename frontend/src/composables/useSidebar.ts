import { ref, computed } from 'vue'

const isCollapsed = ref(false)

export const useSidebar = () => {
  const toggleSidebar = () => {
    isCollapsed.value = !isCollapsed.value
    localStorage.setItem('sidebar-collapsed', isCollapsed.value ? 'true' : 'false')
  }

  const initSidebar = () => {
    const saved = localStorage.getItem('sidebar-collapsed')
    if (saved === 'true') {
      isCollapsed.value = true
    }
  }

  return {
    isCollapsed: computed(() => isCollapsed.value),
    toggleSidebar,
    initSidebar,
  }
}
