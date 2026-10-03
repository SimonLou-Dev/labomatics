<template>
  <div class="relative inline-block">
    <Button
      icon="pi pi-bell"
      severity="secondary"
      text
      rounded
      class="relative"
      @click="toggle"
    />
    <Badge
      v-if="taskCount > 0"
      :value="taskCount"
      severity="danger"
      class="absolute -top-2 -right-2"
    />

    <Panel
      v-if="isOpen"
      class="absolute right-0 top-10 w-96 max-h-96 overflow-auto z-50 shadow-lg"
    >
      <template #header>
        <div class="flex justify-between items-center w-full">
          <span class="font-semibold">Tâches en cours</span>
          <Button
            icon="pi pi-times"
            severity="secondary"
            text
            size="small"
            @click="isOpen = false"
          />
        </div>
      </template>

      <div class="space-y-2">
        <!-- Tâches en cours -->
        <div v-if="tasks.in_progress.length > 0" class="space-y-2">
          <div class="text-xs font-medium text-surface-500">EN COURS</div>
          <div
            v-for="task in tasks.in_progress"
            :key="task.id"
            class="p-2 bg-blue-500/10 border border-blue-500/30 rounded text-xs"
          >
            <div class="font-medium">{{ task.description }}</div>
            <div class="text-surface-400 text-xs">{{ task.type }}</div>
            <div v-if="task.jobs && Object.keys(task.jobs).length > 0" class="mt-1">
              <div
                v-for="(job, jobId) in task.jobs"
                :key="jobId"
                class="text-xs text-surface-500"
              >
                {{ job.description || jobId }}: {{ job.completed_steps }}/{{ job.total_steps }} steps
              </div>
            </div>
          </div>
        </div>

        <!-- Tâches récentes -->
        <div v-if="tasks.completed_recent.length > 0" class="space-y-2">
          <div class="text-xs font-medium text-surface-500">RÉCEMMENT COMPLÉTÉES</div>
          <div
            v-for="task in tasks.completed_recent"
            :key="task.id"
            class="p-2 bg-green-500/10 border border-green-500/30 rounded text-xs"
          >
            <div class="font-medium">{{ task.description }}</div>
            <div class="text-surface-400 text-xs">✓ Complétée</div>
          </div>
        </div>

        <!-- Tâches en erreur -->
        <div v-if="tasks.errors.length > 0" class="space-y-2">
          <div class="text-xs font-medium text-surface-500">ERREURS</div>
          <div
            v-for="task in tasks.errors"
            :key="task.id"
            class="p-2 bg-red-500/10 border border-red-500/30 rounded text-xs"
          >
            <div class="font-medium">{{ task.description }}</div>
            <div class="text-red-400 text-xs">✗ {{ task.error }}</div>
          </div>
        </div>

        <div v-if="taskCount === 0" class="text-center text-surface-400 text-xs py-4">
          Aucune tâche
        </div>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { Button, Badge, Panel } from 'primevue'

interface Job {
  id: string
  description: string
  status: string
  total_steps: number
  completed_steps: number
  error: string | null
  steps?: string[]
}

interface Task {
  id: string
  user_id: string | null
  type: string
  description: string
  status: string
  created_at: string
  started_at: string
  completed_at: string | null
  error: string | null
  jobs: Record<string, Job>
}

interface TasksState {
  in_progress: Task[]
  completed_recent: Task[]
  errors: Task[]
}

const isOpen = ref(false)
const ws = ref<WebSocket | null>(null)
const tasks = ref<TasksState>({
  in_progress: [],
  completed_recent: [],
  errors: [],
})

const taskCount = computed(() => {
  return (
    tasks.value.in_progress.length +
    tasks.value.completed_recent.length +
    tasks.value.errors.length
  )
})

function toggle() {
  isOpen.value = !isOpen.value
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // Extraire l'host et le chemin depuis l'URL API
  const url = new URL(apiUrl)
  const basePath = url.pathname.replace(/\/$/, '')
  const wsUrl = `${protocol}//${url.host}${basePath}/v1/ws/user/tasks`

  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    // Envoyer un message pour demander le replay (tâches < 1min, erreurs, en cours)
    ws.value?.send(JSON.stringify({ type: 'replay' }))
  }

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'tasks_replay') {
      // Replay initial - toutes les tâches
      tasks.value = data.data
    } else if (data.type === 'tasks_update') {
      // Mise à jour en temps réel
      tasks.value = data.data
    }
  }

  ws.value.onerror = (error) => {
    console.error('Task WS error:', error)
  }

  ws.value.onclose = () => {
    console.log('Task WS disconnected')
    setTimeout(connectWebSocket, 3000)
  }
}

onMounted(() => {
  connectWebSocket()
  const pingInterval = setInterval(() => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send('ping')
    }
  }, 2000)

  onBeforeUnmount(() => {
    clearInterval(pingInterval)
    ws.value?.close()
  })
})
</script>
