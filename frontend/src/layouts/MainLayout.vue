<template>
  <div class="flex h-screen bg-surface-0 dark:bg-surface-50">
    <!-- Sidebar -->
    <SidebarLayout class="min-h-192! relative!">
      <Sidebar id="labomatics-sidebar" v-model:open="sidebarVisible" class="!w-64!" :collapsible="isMobile ? 'offcanvas' : 'icon'" :overlay="isMobile" :style="{ width: sidebarVisible ? '16rem' : 'auto' }">
        <SidebarSpacer />
        <SidebarAside>
          <SidebarPanel>
            <SidebarHeader>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton>
                    <img v-if="!sidebarVisible" src="@/assets/logo.svg" class="h-10 mx-auto" />
                    <img v-else src="@/assets/logo-large.svg" class="h-9 mx-auto" />
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarHeader>
            <SidebarContent>
              <SidebarGroup v-for="group in menuItems" :key="group.label">
                <SidebarGroupLabel>{{ group.label }}</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    <SidebarMenuItem v-for="item in group.items" :key="item.label">
                      <SidebarMenuButton @click="item.command()">
                        <component :is="item.icon" :color="isDark ? `rgb(var(--primary-400))` : `rgb(var(--primary-600))`" />
                        <span class="text-primary-lab-600">{{ item.label }}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            </SidebarContent>
            <SidebarFooter>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton class="p-1!" v-if="isDark" @click="toggleTheme">
                    <Sun :color="isDark ? `rgb(var(--primary-400))` : `rgb(var(--primary-600))`"/>
                    <span class="text-primary-lab-400">Thème clair</span>
                  </SidebarMenuButton>
                  <SidebarMenuButton class="p-1!" v-else @click="toggleTheme">
                    <component :is="Moon" :color="isDark ? `rgb(var(--primary-400))` : `rgb(var(--primary-600))`" />
                    <span class="text-primary-lab-600">Thème sombre</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton class="p-1!" v-if="isDyslexia" @click="toggleDyslexia">
                    <Palette :color="isDark ? `rgb(var(--primary-400))` : `rgb(var(--primary-600))`"/>
                    <span class="text-primary-lab-600 dark:text-primary-lab-400">Mode dyslexie ON</span>
                  </SidebarMenuButton>
                  <SidebarMenuButton class="p-1!" v-else @click="toggleDyslexia">
                    <Palette :color="isDark ? `rgb(var(--primary-400))` : `rgb(var(--primary-600))`"/>
                    <span class="text-primary-lab-600 dark:text-primary-lab-400">Mode dyslexie</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton class="p-1!" @click="handleLogout">
                    <component :is="SignOut" :color="`rgb(var(--error))`" />
                    <span class="text-error-lab">Déconnexion</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>

              </SidebarMenu>
            </SidebarFooter>
            <SidebarRail />
          </SidebarPanel>
        </SidebarAside>
      </Sidebar>
      <SidebarMain>
        <Menubar :model="topBarItems">
          <template #start>
            <SidebarTrigger severity="secondary" target="labomatics-sidebar" :text="true" size="small">
              <SidebarIcon />
            </SidebarTrigger>
          </template>

          <template #end>
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
          </template>
        </Menubar>

        <router-view />
      </SidebarMain>
    </SidebarLayout>

    <!-- Main Content -->

  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import Sidebar from 'primevue/sidebar';
import { Avatar } from 'primevue';
import SidebarAside from 'primevue/sidebaraside';
import SidebarContent from 'primevue/sidebarcontent';
import SidebarFooter from 'primevue/sidebarfooter';
import SidebarGroup from 'primevue/sidebargroup';
import SidebarGroupContent from 'primevue/sidebargroupcontent';
import SidebarGroupLabel from 'primevue/sidebargrouplabel';
import SidebarHeader from 'primevue/sidebarheader';
import SidebarMain from 'primevue/sidebarmain';
import SidebarLayout from 'primevue/sidebarlayout';
import SidebarMenu from 'primevue/sidebarmenu';
import Menubar from 'primevue/menubar';
import SidebarMenuButton from 'primevue/sidebarmenubutton';
import SidebarMenuItem from 'primevue/sidebarmenuitem';

import SidebarIcon from '@primeicons/vue/sidebar';
import SidebarPanel from 'primevue/sidebarpanel';
import SidebarRail from 'primevue/sidebarrail';
import SidebarSpacer from 'primevue/sidebarspacer';
import SidebarTrigger from 'primevue/sidebartrigger';

import Home from '@primeicons/vue/home';
import User from '@primeicons/vue/user';
import Users from '@primeicons/vue/users';
import Book from '@primeicons/vue/book';
import Pencil from '@primeicons/vue/pencil';
import Cog from '@primeicons/vue/cog';
import Server from '@primeicons/vue/server';
import Sun from '@primeicons/vue/sun';
import Moon from '@primeicons/vue/moon';
import Palette from '@primeicons/vue/palette';
import SignOut from '@primeicons/vue/sign-out';


const router = useRouter()
const auth = useAuthStore()
const { isDark, isDyslexia, toggleTheme, toggleDyslexia } = useTheme()

const sidebarVisible = ref(true)
const userMenu = ref()
const isMobile = ref(false)
let mql: MediaQueryList | null = null
let onMqlChange: ((event: MediaQueryListEvent) => void) | null = null

const user = computed(() => auth.user)
const hasRole = (role: string) => auth.hasRole(role)

onMounted(() => {
  if (typeof window === 'undefined') return

  mql = window.matchMedia('(max-width: 1023px)')
  isMobile.value = mql.matches
  sidebarVisible.value = !isMobile.value

  onMqlChange = (event) => {
    isMobile.value = event.matches
    sidebarVisible.value = !event.matches
  }

  mql.addEventListener('change', onMqlChange)
})

onBeforeUnmount(() => {
  if (mql && onMqlChange) {
    mql.removeEventListener('change', onMqlChange)
  }
})

const handleLogout = async () => {
  await auth.logoutUser()
}

const topBarItems = ref([])

// Menu items organized by role
const menuItems = computed(() => {

  const items: any[] = [
    {
      label: "Navigation",
      items: [
        {
          label: 'Dashboard',
          icon: Home,
          command: () => router.push('/'),
        },
        {
          label: 'Mon compte',
          icon: User,
          command: () => router.push('/'),
        }
      ]
    }
  ]

  if (hasRole('student')) {
    items.push({
      label: 'Étudiant',
      items: [
        {
          label: 'Dashboard',
          icon: Home,
          command: () => router.push('/'),
        },
        {
          label: 'Mon compte',
          icon: User,
          command: () => router.push('/account'),
        },
        {
          label: 'Mon lab',
          icon: User,
          command: () => router.push('/lab'),
        },
      ],
    })
  }

  if (hasRole('teacher')) {
    items.push({
      label: 'Professeur',
      items: [
        {
          label: 'Travaux pratiques',
          icon: Pencil,
          command: () => router.push('/tps'),
        },
        {
          label: 'Classes',
          icon: Book,
          command: () => router.push('/cohorts'),
        },
      ],
    })
  }

  if (hasRole('admin')) {
    items.push({
      label: 'Administration',
      items: [
        {
          label: 'Étudiants',
          icon: Users,
          command: () => router.push('/students'),
        },
        {
          label: 'Paramètres',
          icon: Cog,
          command: () => router.push('/admin/settings'),
        },
        {
          label: 'Cluster',
          icon: Server,
          command: () => router.push('/cluster'),
        }
      ],
    })
  }

  return items
})



// Close sidebar on navigation
watch(() => router.currentRoute.value.path, () => {
  sidebarVisible.value = false
}, { immediate: false })

onMounted(() => {
  // On mobile, start with sidebar closed
  if (window.innerWidth < 768) {
    sidebarVisible.value = false
  }
})
</script>
