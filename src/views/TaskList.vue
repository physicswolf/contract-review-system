<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>分析任务</span>
        <el-button @click="loadTasks" :loading="loading">刷新</el-button>
      </div>
    </template>

    <el-table :data="tasks" v-loading="loading" empty-text="暂无任务">
      <el-table-column prop="filename" label="文件名" min-width="220" />
      <el-table-column prop="file_type" label="类型" width="80" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="page_count" label="页数" width="80">
        <template #default="{ row }">{{ row.page_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="上传时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/tasks/${row.id}`)">查看</el-button>
          <el-button link type="warning" @click="handleReanalyze(row.id)">重分析</el-button>
          <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteDocument, listDocuments, reanalyzeDocument } from '../api/document'

const tasks = ref([])
const loading = ref(false)

const STATUS_MAP = {
  pending: { label: '待处理', type: 'info' },
  parsing: { label: '解析中', type: 'warning' },
  parsed: { label: '已解析', type: 'warning' },
  analyzing: { label: '分析中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

function statusLabel(status) {
  return STATUS_MAP[status]?.label || status
}

function statusType(status) {
  return STATUS_MAP[status]?.type || 'info'
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

async function loadTasks() {
  loading.value = true
  try {
    const data = await listDocuments()
    tasks.value = data.items
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleReanalyze(id) {
  try {
    await reanalyzeDocument(id)
    ElMessage.success('已重新提交分析')
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除该任务及文件？', '提示', { type: 'warning' })
    await deleteDocument(id)
    ElMessage.success('已删除')
    await loadTasks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(loadTasks)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
