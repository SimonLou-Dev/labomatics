import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import MainLayout from '@/layouts/MainLayout.vue'
import LoginPage from '@/pages/Login.vue'
import ForbiddenPage from '@/pages/Forbidden.vue'
import StudentsAdminPage from '@/pages/admin/Students.vue'
import ClustersPage from '@/pages/admin/Clusters.vue'
import WanRangesPage from '@/pages/admin/WanRanges.vue'
import NetworkRangesPage from '@/pages/admin/NetworkRanges.vue'
import WanRangeDetailsPage from '@/pages/admin/WanRangeDetails.vue'
import NetworkRangeDetailsPage from '@/pages/admin/NetworkRangeDetails.vue'
import LabPage from '@/pages/Lab.vue'
import AdminCohortsPage from '@/pages/admin/Cohorts.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
    meta: { requiresAuth: false, layout: 'blank' },
  },
  {
    path: '/forbidden',
    name: 'Forbidden',
    component: ForbiddenPage,
    meta: { requiresAuth: false, layout: 'blank' },
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: LabPage,
      },
      {
        path: 'admin/students',
        name: 'Students',
        component: StudentsAdminPage,
        meta: { roles: ['manage_user'] },
      },
      {
        path: 'admin/cluster',
        name: 'Clusters',
        component: ClustersPage,
        meta: { roles: ['manage_cluster'] },
      },
      {
        path: 'admin/wan',
        name: 'WanRanges',
        component: WanRangesPage,
        meta: { roles: ['manage_cluster'] },
      },
      {
        path: 'admin/wan/:rangeId',
        name: 'WanRangeDetails',
        component: WanRangeDetailsPage,
        meta: { roles: ['manage_cluster'] },
      },
      {
        path: 'admin/networks',
        name: 'NetworkRanges',
        component: NetworkRangesPage,
        meta: { roles: ['manage_cluster'] },
      },
      {
        path: 'admin/networks/:rangeId',
        name: 'NetworkRangeDetails',
        component: NetworkRangeDetailsPage,
        meta: { roles: ['manage_cluster'] },
      },
      {
        path: 'admin/cohorts',
        name: 'AdminCohorts',
        component: AdminCohortsPage,
        meta: { roles: ['manage_cluster'] },
      },
      {
        path: 'lab/:userId?',
        name: 'Lab',
        component: LabPage,
      },
      {
        path: 'cohorts',
        name: 'Cohorts',
        component: AdminCohortsPage,
        meta: { roles: ['manage_cluster'] },
      },
      {
        path: 'labs',
        name: 'Labs',
        component: { template: '<div class="p-6"><h1>Labs</h1></div>' },
      },
      {
        path: 'admin/users',
        name: 'AdminUsers',
        component: { template: '<div class="p-6"><h1>Utilisateurs</h1></div>' },
      },
      {
        path: 'admin/settings',
        name: 'AdminSettings',
        component: { template: '<div class="p-6"><h1>Paramètres</h1></div>' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  const requiredRoles = to.meta.roles as string[] | undefined

  if (to.meta.requiresAuth && !auth.user) {
    next('/login')
  } else if (to.path === '/login' && auth.user) {
    next('/')
  } else if (requiredRoles && !requiredRoles.some((role) => auth.hasRole(role))) {
    // Garde-fou côté UI uniquement : l'autorité reste le backend (403 sur les routes API).
    next('/forbidden')
  } else {
    next()
  }
})

export default router
