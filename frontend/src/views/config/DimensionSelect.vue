<template>
  <AppTopbar title="配置中心 · 审核维度">
    <template #actions>
      <el-button @click="router.push({ name: 'config' })">返回审核点管理</el-button>
    </template>
  </AppTopbar>

  <div class="page">
    <div class="page-head">
      <h1>审核维度</h1>
      <p>选择或确认审核点所属维度，下一步进入配置审核维度。</p>
    </div>

    <el-card shadow="never" v-loading="loading">
      <h3 class="card-title">选择审核维度</h3>
      <p class="card-sub">系统会基于所选维度带入默认配置，后续仍可在"配置审核维度"页面调整。</p>

      <div class="dim-grid">
        <div
          v-for="d in dims"
          :key="d.name"
          class="dim-card"
          :class="{ on: selected === d.name }"
          @click="selected = d.name"
        >
          <div class="dc-head">
            <b>{{ d.name }}</b>
            <span v-if="selected === d.name" class="picked">已选择</span>
          </div>
          <p>{{ d.desc }}</p>
        </div>
      </div>

      <div class="actions">
        <el-button @click="router.push({ name: 'configDimensions' })">取消</el-button>
        <el-button type="primary" @click="next">下一步</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppTopbar from '../../components/AppTopbar.vue'
import { listSelectableDimensions } from '../../services/dimension.service'

const router = useRouter()
const loading = ref(false)
const dims = ref([])
const selected = ref('法务风险')

onMounted(async () => {
  loading.value = true
  try {
    dims.value = await listSelectableDimensions()
  } finally {
    loading.value = false
  }
})

function next() {
  ElMessage.success(`已选择「${selected.value}」，进入配置审核维度`)
  router.push({ name: 'configDimensions' })
}
</script>

<style scoped>
.page {
  flex: 1;
  padding: 24px 28px;
  overflow: auto;
}
.page-head h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.page-head p {
  margin: 8px 0 16px;
  color: var(--muted);
}
.card-title {
  margin: 0 0 4px;
  font-size: 16px;
}
.card-sub {
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 13px;
}
.dim-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.dim-card {
  border: 0.667px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.15s;
}
.dim-card:hover {
  border-color: #b9c5e8;
}
.dim-card.on {
  background: #f3f5ff;
  border-color: var(--blue);
}
.dc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.dc-head b {
  font-size: 15px;
}
.picked {
  font-size: 11px;
  color: #fff;
  background: var(--blue);
  padding: 2px 8px;
  border-radius: 6px;
}
.dim-card p {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.6;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
</style>
