<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="brand" @click="$router.push('/')">
        <span class="title">合同 AI 分析系统</span>
        <span class="subtitle">课题研究 · 内部参考</span>
      </div>
      <el-menu mode="horizontal" :ellipsis="false" router :default-active="activeMenu">
        <el-menu-item index="/">上传分析</el-menu-item>
        <el-menu-item index="/tasks">任务列表</el-menu-item>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => {
  if (route.path.startsWith('/tasks')) return '/tasks'
  return '/'
})
</script>

<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: #f5f7fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', sans-serif;
}
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 0 24px;
}
.brand {
  cursor: pointer;
}
.title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.subtitle {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}
.el-main {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
</style>
