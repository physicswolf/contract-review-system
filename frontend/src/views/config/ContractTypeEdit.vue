<template>
  <AppTopbar title="配置中心 · 合同类型编辑">
    <template #actions>
      <el-button @click="backToTypes">返回合同类型管理</el-button>
    </template>
  </AppTopbar>

  <div class="page">
    <div class="type-shell">
      <aside class="type-aside">
        <div class="type-aside-title">合同类型 · 立场</div>
        <div class="type-list" v-loading="loadingTypes">
          <button
            v-for="item in types"
            :key="item.id"
            class="type-item"
            :class="{ on: !isNew && String(item.id) === currentTypeId }"
            @click="openType(item)"
          >
            <b>
              <span class="dot" :style="{ background: item.status === '已启用' ? '#20b879' : '#cbd3df' }"></span>
              {{ item.name }}
            </b>
            <span>{{ item.stance }} · {{ item.relatedPoints }} 个审查点</span>
          </button>
        </div>
        <div class="type-add">
          <el-button style="width: 100%" :type="isNew ? 'primary' : 'default'" @click="newType">＋ 新建</el-button>
        </div>
      </aside>

      <main class="type-main">
        <div class="page-head">
          <h1>{{ isNew ? '新建合同类型' : '编辑合同类型' }}</h1>
          <p>定义合同类型、审核立场及合同关键信息识别范围</p>
        </div>

        <section class="card" v-loading="loading">
          <div class="dlg-grid">
            <div class="field">
              <label>合同类型 <span class="req">*</span></label>
              <el-input v-model="form.name" placeholder="请输入合同类型名称" />
            </div>
            <div class="field">
              <label>合同立场 <span class="req">*</span></label>
              <el-select v-model="form.stance" class="full">
                <el-option label="甲方立场" value="甲方立场" />
                <el-option label="乙方立场" value="乙方立场" />
              </el-select>
            </div>
            <div class="field wide">
              <label>合同描述</label>
              <el-input v-model="form.desc" type="textarea" :rows="3" placeholder="请输入该合同类型的定义、适用范围及主要业务特征" />
            </div>
            <div class="field wide">
              <label>识别关键词</label>
              <el-input v-model="form.keywords" placeholder="多个关键词用逗号分隔，如：采购,供货,设备" />
              <div class="field-hint">大模型依据关键词和合同描述进行自动识别</div>
            </div>
          </div>
        </section>

        <div class="actions">
          <div class="actions-left">
            <el-button v-if="!isNew" type="danger" plain @click="deleteType">删除该合同类型</el-button>
          </div>
          <div class="actions-right">
            <el-button @click="backToTypes">取消</el-button>
            <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppTopbar from '../../components/AppTopbar.vue'
import { deleteType as deleteTypeApi, getType, listTypes, saveType } from '../../services/type.service'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'contractTypeNew' || route.params.id === 'new')
const currentTypeId = computed(() => String(route.params.id || ''))
const loading = ref(false)
const loadingTypes = ref(false)
const saving = ref(false)
const types = ref([])

const form = reactive({
  id: '',
  name: '',
  stance: '甲方立场',
  desc: '',
  keywords: '',
})

onMounted(loadTypes)

watch(
  () => [route.name, route.params.id],
  () => {
    loadForm()
  },
  { immediate: true },
)

async function loadTypes() {
  loadingTypes.value = true
  try {
    const { items } = await listTypes()
    types.value = items
  } finally {
    loadingTypes.value = false
  }
}

async function loadForm() {
  if (!isNew.value) {
    loading.value = true
    try {
      const detail = await getType(route.params.id)
      if (detail) {
        form.id = detail.id
        form.name = detail.name || ''
        form.stance = detail.stance || '甲方立场'
        form.desc = detail.desc || ''
        form.keywords = Array.isArray(detail.keywords) ? detail.keywords.join(',') : (detail.keywords || '')
      }
    } finally {
      loading.value = false
    }
    return
  }

  Object.assign(form, {
    id: '',
    name: '',
    stance: '甲方立场',
    desc: '',
    keywords: '',
  })
}

function openType(item) {
  router.push({ name: 'contractTypeEdit', params: { id: item.id } })
}

function newType() {
  router.push({ name: 'contractTypeNew' })
}

async function save() {
  if (!form.name) {
    ElMessage.warning('请填写合同类型名称')
    return
  }
  saving.value = true
  try {
    await saveType({
      id: isNew.value ? undefined : form.id,
      name: form.name,
      stance: form.stance,
      desc: form.desc,
      keywords: form.keywords,
    })
    ElMessage.success('保存成功')
    backToTypes()
  } finally {
    saving.value = false
  }
}

async function deleteType() {
  await ElMessageBox.confirm(
    `确认删除合同类型「${form.name}」？删除后可在数据库中恢复。`,
    '提示',
    { type: 'warning' },
  )
  await deleteTypeApi(form.id)
  ElMessage.success('已删除')
  backToTypes()
}

function backToTypes() {
  router.push({ name: 'config', query: { tab: 'types' } })
}
</script>

<style scoped>
.page {
  flex: 1;
  padding: 20px 28px 30px;
  overflow: auto;
}
.type-shell {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  min-height: 600px;
  background: #fff;
  border: 0.667px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}
.type-aside {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fbfcff;
  border-right: 0.667px solid #e0e6ef;
}
.type-aside-title {
  padding: 16px 18px;
  font-size: 13.5px;
  font-weight: 700;
  border-bottom: 0.667px solid #e7ecf4;
}
.type-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  overflow-y: auto;
}
.type-item {
  width: 100%;
  padding: 12px 14px;
  text-align: left;
  color: var(--ink);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
}
.type-item:hover {
  background: #f5f6ff;
}
.type-item.on {
  border-color: #dfe4ff;
  background: #f0f2ff;
}
.type-item b,
.type-item span {
  display: block;
}
.type-item b {
  font-size: 14px;
}
.type-item span {
  margin-top: 4px;
  color: #8a96aa;
  font-size: 12px;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 7px;
  border-radius: 50%;
}
.type-add {
  margin: 12px;
  padding-top: 12px;
  border-top: 0.667px solid #e7ecf4;
}
.type-main {
  min-width: 0;
  padding: 26px 30px 30px;
}
.page-head h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.page-head p {
  margin: 8px 0 18px;
  color: var(--muted);
}
.card {
  background: #fff;
  border: 0.667px solid var(--line);
  border-radius: 8px;
  padding: 22px;
  margin-bottom: 18px;
}
.dlg-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.field {
  margin-bottom: 4px;
}
.field.wide {
  grid-column: 1 / -1;
}
.field label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #526077;
}
.req {
  color: var(--red);
}
.full {
  width: 100%;
}
.field-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
}
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 30px;
}
.actions-left,
.actions-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
