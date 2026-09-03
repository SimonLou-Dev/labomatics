import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import MainLayout from '@/layouts/MainLayout.vue'
import LoginPage from '@/pages/Login.vue'
import ForbiddenPage from '@/pages/Forbidden.vue'
import DashboardPage from '@/pages/Dashboard.vue'
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
        component: DashboardPage,
      },
      {
        path: 'admin/students',
        name: 'Students',
        component: StudentsAdminPage,
      },
      {
        path: 'admin/cluster',
        name: 'Clusters',
        component: ClustersPage,
      },
      {
        path: 'admin/wan',
        name: 'WanRanges',
        component: WanRangesPage,
      },
      {
        path: 'admin/wan/:rangeId',
        name: 'WanRangeDetails',
        component: WanRangeDetailsPage,
      },
      {
        path: 'admin/networks',
        name: 'NetworkRanges',
        component: NetworkRangesPage,
      },
      {
        path: 'admin/networks/:rangeId',
        name: 'NetworkRangeDetails',
        component: NetworkRangeDetailsPage,
      },
      {
        path: 'admin/cohorts',
        name: 'AdminCohorts',
        component: AdminCohortsPage,
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

  if (to.meta.requiresAuth && !auth.user) {
    next('/login')
  } else if (to.path === '/login' && auth.user) {
    next('/')
  } else {
    next()
  }
})

export default router
