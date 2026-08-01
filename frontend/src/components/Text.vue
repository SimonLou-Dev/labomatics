<template>
  <span :class="[sizeClasses, { 'text-gray-600 dark:text-gray-400': secondary }]">
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: 'caption' | 'small' | 'body'
  secondary?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'body',
  secondary: false,
})

const sizeClasses = computed(() => {
  const sizes = {
    caption: 'text-xs leading-tight',
    small: 'text-sm leading-normal',
    body: 'text-base leading-normal',
  }
  return sizes[props.size]
})
</script>
