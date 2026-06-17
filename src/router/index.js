import { createRouter, createWebHistory } from 'vue-router'
import Upload from '../views/Upload.vue'
import TaskList from '../views/TaskList.vue'
import Result from '../views/Result.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'upload', component: Upload },
    { path: '/tasks', name: 'tasks', component: TaskList },
    { path: '/tasks/:id', name: 'result', component: Result },
  ],
})

export default router
