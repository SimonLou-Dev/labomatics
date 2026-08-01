import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import MainLayout from '@/layouts/MainLayout.vue'
import LoginPage from '@/pages/Login.vue'
import DashboardPage from '@/pages/Dashboard.vue'
import StudentsPage from '@/pages/Students.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
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
        path: 'students',
        name: 'Students',
        component: StudentsPage,
      },
      {
        path: 'cohorts',
        name: 'Cohorts',
        component: { template: '<div class="p-6"><h1>Classes</h1></div>' },
      },
      {
        path: 'labs',
        name: 'Labs',
        component: { template: '<div class="p-6"><h1>Laboratoires</h1></div>' },
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
