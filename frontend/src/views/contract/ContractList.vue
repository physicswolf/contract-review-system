<template>
  <AppTopbar title="应用中心">
    <template #actions>
      <span>共 {{ rows.length }} 份合同</span>
    </template>
  </AppTopbar>

  <div class="page">
    <div class="title-row">
      <div>
        <h1>合同列表</h1>
        <p>检索合同并查看对应审核结果</p>
      </div>
    </div>

    <div class="search">
      <el-input v-model="q.name" placeholder="合同名称" clearable />
      <el-input v-model="q.partyA" placeholder="甲方" clearable />
      <el-input v-model="q.partyB" placeholder="乙方" clearable />
      <el-button type="primary" @click="load">检索</el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <el-card shadow="never" body-style="padding:0">
      <el-table :data="rows" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="合同名称" min-width="200" />
        <el-table-column prop="partyA" label="甲方" min-width="170" />
        <el-table-column prop="partyB" label="乙方" min-width="170" />
        <el-table-column prop="type" label="合同类型" width="110" />
        <el-table-column label="风险" width="110">
          <template #default="{ row }">
            <RiskTag :level="row.riskLevel" :text="row.riskCount ? `${row.risk} ${row.riskCount}` : row.risk" />
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="审核时间" width="120" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openResult(row)">查看审核结果</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppTopbar from '../../components/AppTopbar.vue'
import RiskTag from '../../components/RiskTag.vue'
import { listContracts, deleteContract } from '../../services/contract.service'

const router = useRouter()
const loading = ref(false)
const rows = ref([])
const q = reactive({ name: '', partyA: '', partyB: '' })

onMounted(load)
async function load() {
  loading.value = true
  try {
    const { items } = await listContracts({ ...q })
    rows.value = items
  } finally {
    loading.value = false
  }
}
function reset() {
  q.name = q.partyA = q.partyB = ''
  load()
}
function openResult(row) {
  router.push({ name: 'result', params: { id: row.id } })
}
async function remove(row) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
  await deleteContract(row.id)
  ElMessage.success('已删除')
  load()
}
</script>

<style scoped>
.page {
  flex: 1;
  padding: 24px 28px;
  overflow: auto;
}
.title-row h1 {
  margin: 0;
  font-size: 22px;
}
.title-row p {
  margin: 6px 0 0;
  color: var(--muted);
}
.search {
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 20px 0 16px;
}
.search .el-input {
  flex: 1;
  max-width: 320px;
}
</style>
