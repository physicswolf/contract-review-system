<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-body">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
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
  height: 100vh;
  overflow: hidden;
}
.app-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}
</style>
