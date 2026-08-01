<template>
  <input
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    class="w-full px-3 py-2 text-base font-sans text-gray-900 bg-white border border-gray-300 rounded-lg transition-all focus:outline-none focus:border-primary-500 focus:ring-3 focus:ring-primary-500/10 disabled:opacity-60 disabled:cursor-not-allowed disabled:bg-gray-50 placeholder:text-gray-500 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-50 dark:placeholder:text-gray-400"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<script setup lang="ts">
interface Props {
  modelValue: string
  type?: 'text' | 'email' | 'password'
  placeholder?: string
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  type: 'text',
  disabled: false,
})

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>
