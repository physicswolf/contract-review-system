<template>
  <aside class="sidebar">
    <div class="brand">
      <span class="logo">AI</span>
      <span class="brand-name">AI智契</span>
    </div>

    <div class="nav">
      <template v-for="group in groups" :key="group.label">
        <div class="nav-label">{{ group.label }}</div>
        <button
          v-for="item in group.items"
          :key="item.name"
          class="side-link"
          :class="{ on: isActive(item) }"
          @click="go(item)"
        >
          <el-icon class="ico"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
      </template>
    </div>

    <div class="side-foot" @click="router.push({ name: 'profile' })">
      <span class="avatar">{{ avatar }}</span>
      <span class="foot-name">{{ name }}<br /><small>{{ role }}</small></span>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { userStore } from '../stores/user'

const route = useRoute()
const router = useRouter()

const groups = [
  {
    label: '核心功能',
    items: [
      { name: 'review', label: '合同审核', icon: 'EditPen' },
      { name: 'contracts', label: '应用中心', icon: 'Menu' },
    ],
  },
  {
    label: '管理',
    items: [{ name: 'config', label: '配置中心', icon: 'Setting', match: 'config' }],
  },
]

function isActive(item) {
  if (item.match === 'config') return route.path.startsWith('/config')
  if (item.name === 'review') return route.name === 'review' || route.name === 'structureEditor'
  if (item.name === 'contracts') return route.name === 'contracts' || route.name === 'result'
  return route.name === item.name
}
function go(item) {
  router.push({ name: item.name })
}

const name = computed(() => userStore.profile?.name || '伊路')
const role = computed(() => userStore.profile?.role || '企业管理员')
const avatar = computed(() => (name.value || 'U').slice(0, 2).toUpperCase())
</script>

<style scoped>
.sidebar {
  width: 224px;
  flex-shrink: 0;
  background: linear-gradient(180deg, #081326 0%, #06101f 100%);
  color: #cbd5e6;
  display: flex;
  flex-direction: column;
  padding: 20px 13px;
  height: 100vh;
  position: sticky;
  top: 0;
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  font-weight: 700;
  color: #fff;
  font-size: 19px;
  padding: 0 10px 24.67px;
  border-bottom: 0.667px solid #1e304c;
}
.logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 19px;
  background: linear-gradient(135deg, #586ff5 0%, #25c9bb 100%);
  box-shadow: 0 10px 12px rgba(89, 111, 245, 0.27);
  color: #fff;
}
.nav {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.nav-label {
  margin: 10px 12px 2px;
  font-size: 11px;
  letter-spacing: 1px;
  color: #5d6e88;
}
.nav-label:first-child {
  margin-top: 0;
}
.side-link {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  border: 0.667px solid transparent;
  background: transparent;
  color: #91a0b8;
  height: 44px;
  padding: 0 13.67px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.15s;
}
.side-link .ico {
  font-size: 17px;
}
.side-link:hover {
  color: #d6deec;
}
.side-link.on {
  background: linear-gradient(90deg, rgba(89, 111, 245, 0.85) 0%, rgba(89, 111, 245, 0.17) 100%);
  border-color: rgba(100, 121, 255, 0.4);
  box-shadow: 0 10px 25px rgba(32, 55, 140, 0.21);
  color: #fff;
}
.side-foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12.67px 12px 12px;
  border-top: 0.667px solid #1e304c;
  cursor: pointer;
}
.side-foot:hover .foot-name {
  color: #cdd7e6;
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 17px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: #263e66;
  color: #dbe6fa;
  font-weight: 800;
  font-size: 12px;
}
.foot-name {
  font-size: 12px;
  color: #94a2b9;
  line-height: 1.45;
}
.foot-name small {
  color: #94a2b9;
  font-size: 12px;
}
</style>
