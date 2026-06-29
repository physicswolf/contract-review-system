<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-body">
      <RouterView />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppSidebar from '../components/AppSidebar.vue'
import { userStore } from '../stores/user'
import { getProfile } from '../services/auth.service'

onMounted(async () => {
  if (userStore.isLoggedIn && !userStore.profile) {
    try {
      userStore.setProfile(await getProfile())
    } catch {
      /* 拦截器已处理 */
    }
  }
})
</script>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
}
.app-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}
</style>
