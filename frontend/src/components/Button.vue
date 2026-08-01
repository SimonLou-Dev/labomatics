<template>
  <button
    :class="['btn', variantClass, sizeClass, { 'btn-disabled': disabled }]"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'error' | 'success'
  size?: 'xs' | 'sm' | 'md' | 'lg'
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
})

const variantClass = computed(() => {
  const map: Record<string, string> = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    outline: 'btn-outline',
    ghost: 'btn-ghost',
    error: 'btn-error',
    success: 'btn-success',
  }
  return map[props.variant] || 'btn-primary'
})

const sizeClass = computed(() => {
  const map: Record<string, string> = {
    xs: 'btn-xs',
    sm: 'btn-sm',
    md: 'btn-md',
    lg: 'btn-lg',
  }
  return map[props.size] || 'btn-md'
})

defineEmits<{ click: [] }>()
</script>
