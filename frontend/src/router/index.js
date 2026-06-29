import { createRouter, createWebHistory } from 'vue-router'
import { userStore } from '../stores/user'

import MainLayout from '../layouts/MainLayout.vue'
import Login from '../views/Login.vue'

const routes = [
  { path: '/login', name: 'login', component: Login, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: { name: 'review' } },
      { path: 'review', name: 'review', component: () => import('../views/review/ReviewWizard.vue') },
      { path: 'contracts', name: 'contracts', component: () => import('../views/contract/ContractList.vue') },
      { path: 'contracts/:id/result', name: 'result', component: () => import('../views/contract/AuditResult.vue') },

      { path: 'config', name: 'config', component: () => import('../views/config/ConfigCenter.vue') },
      { path: 'config/dimensions', name: 'configDimensions', component: () => import('../views/config/DimensionManage.vue') },
      { path: 'config/dimensions/select', name: 'dimensionSelect', component: () => import('../views/config/DimensionSelect.vue') },
      { path: 'config/points/:id/edit', name: 'pointEdit', component: () => import('../views/config/PointEdit.vue') },

      { path: 'profile', name: 'profile', component: () => import('../views/Profile.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: { name: 'review' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (!to.meta.public && !userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && userStore.isLoggedIn) {
    return { name: 'review' }
  }
})

export default router
