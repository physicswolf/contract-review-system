<template>
  <AppTopbar title="配置中心 · 审核维度管理">
    <template #actions>
      <el-button @click="router.push({ name: 'config' })">返回审核点管理</el-button>
    </template>
  </AppTopbar>

  <div class="page">
    <div class="page-head">
      <div>
        <h1>审核维度管理</h1>
        <p>维护审核维度，支持新建、编辑、删除；保存维度后回到当前维度列表。</p>
      </div>
      <el-button type="primary" @click="openDialog()">＋ 新建维度</el-button>
    </div>

    <el-card shadow="never" body-style="padding:0">
      <el-table :data="rows" v-loading="loading">
        <el-table-column prop="name" label="维度名称" min-width="160">
          <template #default="{ row }"><b>{{ row.name }}</b></template>
        </el-table-column>
        <el-table-column prop="desc" label="维度说明" min-width="300" show-overflow-tooltip />
        <el-table-column label="状态" width="150">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status === '已启用'"
              @change="(v) => toggleStatus(row, v)"
            />
            <span class="status-text">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="120" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="form.id ? '编辑维度' : '新建维度'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="维度名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="维度说明">
          <el-input v-model="form.desc" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppTopbar from '../../components/AppTopbar.vue'
import {
  listDimensionDetail,
  saveDimension,
  deleteDimension,
} from '../../services/dimension.service'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const rows = ref([])
const form = reactive({ id: '', name: '', desc: '' })

onMounted(load)
async function load() {
  loading.value = true
  try {
    const { items } = await listDimensionDetail()
    rows.value = items
  } finally {
    loading.value = false
  }
}
function openDialog(row) {
  Object.assign(form, { id: '', name: '', desc: '' }, row || {})
  dialog.value = true
}
async function save() {
  if (!form.name) {
    ElMessage.warning('请填写维度名称')
    return
  }
  saving.value = true
  try {
    await saveDimension({ ...form, id: form.id || undefined })
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}
async function toggleStatus(row, v) {
  await saveDimension({ id: row.id, status: v ? '已启用' : '已停用' })
  row.status = v ? '已启用' : '已停用'
}
async function remove(row) {
  await ElMessageBox.confirm(`确认删除维度「${row.name}」？`, '提示', { type: 'warning' })
  await deleteDimension(row.id)
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
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
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
.status-text {
  margin-left: 8px;
  font-size: 13px;
  color: var(--muted);
}
</style>
