<template>
  <div class="flex flex-col gap-2">
    <label v-if="label" :for="id" class="font-medium text-gray-900 cursor-pointer flex gap-1 dark:text-gray-50">
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <slot />
    <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
    <p v-if="hint" class="text-sm text-gray-500 dark:text-gray-400">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  id?: string
  label?: string
  error?: string
  hint?: string
  required?: boolean
}

const props = defineProps<Props>()

const id = computed(() => props.id || `field-${Math.random()}`)
</script>
