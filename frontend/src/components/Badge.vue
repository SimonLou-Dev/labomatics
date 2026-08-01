<template>
  <span :class="['inline-flex items-center justify-center font-semibold whitespace-nowrap rounded-lg transition-all', sizeClasses, colorClasses]">
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  color?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info'
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  color: 'default',
  size: 'md',
})

const sizeClasses = computed(() => {
  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
  }
  return sizes[props.size]
})

const colorClasses = computed(() => {
  const colors = {
    default: 'bg-gray-100 text-gray-900 border border-gray-300 dark:bg-gray-700 dark:text-gray-50 dark:border-gray-600',
    primary: 'bg-primary-500 text-white',
    success: 'bg-green-500 text-white',
    warning: 'bg-amber-500 text-white',
    error: 'bg-red-500 text-white',
    info: 'bg-blue-500 text-white',
  }
  return colors[props.color]
})
</script>
