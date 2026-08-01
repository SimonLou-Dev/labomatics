<template>
  <component :is="tag" :class="['font-bold leading-tight', sizeClasses]">
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  level?: 1 | 2 | 3 | 4
}

const props = withDefaults(defineProps<Props>(), {
  level: 1,
})

const tag = computed(() => `h${props.level}`)

const sizeClasses = computed(() => {
  const sizes = {
    1: 'text-3xl mb-6',
    2: 'text-2xl mb-4',
    3: 'text-xl mb-3',
    4: 'text-lg mb-2',
  }
  return sizes[props.level]
})
</script>
