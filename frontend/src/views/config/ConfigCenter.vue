<template>
  <AppTopbar title="配置中心" />

  <div class="page">
    <div class="cfg-tabs">
      <button class="cfg-tab" :class="{ on: tab === 'points' }" @click="tab = 'points'">审核点管理</button>
      <button class="cfg-tab" :class="{ on: tab === 'types' }" @click="tab = 'types'">合同类型管理</button>
    </div>

    <!-- 审核点管理 -->
    <section v-show="tab === 'points'">
      <div class="head">
        <div><h1>审核点管理</h1><p>统一维护审核点及其风险点信息</p></div>
        <div class="head-actions">
          <el-button @click="router.push({ name: 'configDimensions' })">维度管理</el-button>
          <el-button type="primary" @click="router.push({ name: 'pointEdit', params: { id: 'new' } })">＋ 新建审核点</el-button>
        </div>
      </div>
      <div class="search">
        <el-input v-model="pointKw" placeholder="搜索审核点名称" clearable @keyup.enter="loadPoints" />
        <el-button type="primary" @click="loadPoints">检索</el-button>
        <el-button @click="pointKw = ''; loadPoints()">重置</el-button>
      </div>
      <el-card shadow="never" body-style="padding:0">
        <el-table :data="points" v-loading="loadingPoints">
          <el-table-column prop="name" label="审核点名称" min-width="150" />
          <el-table-column prop="desc" label="审核点说明" min-width="240" show-overflow-tooltip />
          <el-table-column prop="dimension" label="审核维度" width="120" />
          <el-table-column label="风险点" width="90">
            <template #default="{ row }">{{ row.riskPoints }} 个</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-switch :model-value="row.status === '已启用'" @change="(v) => togglePoint(row, v)" />
            </template>
          </el-table-column>
          <el-table-column prop="updatedAt" label="更新时间" width="110" />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push({ name: 'pointEdit', params: { id: row.id } })">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager"><span>共 {{ points.length }} 个审核点</span></div>
      </el-card>
    </section>

    <!-- 合同类型管理 — 左列表 + 右编辑器 -->
    <section v-show="tab === 'types'" class="type-shell">
      <!-- 左侧列表 -->
      <aside class="type-aside">
        <div class="type-aside-title">合同类型 · 立场</div>
        <div class="type-list" v-loading="loadingTypes">
          <div
            v-for="t in types" :key="t.id"
            class="type-item" :class="{ on: currentType?.id === t.id }"
            @click="selectType(t)"
          >
            <b><span class="dot" :style="{ background: t.status === '已启用' ? '#20b879' : '#cbd3df' }"></span>{{ t.name }}</b>
            <span>{{ t.stance }} · {{ t.relatedPoints }} 个审查点</span>
          </div>
        </div>
        <div class="type-add">
          <el-button style="width:100%" @click="newType">＋ 新建</el-button>
        </div>
      </aside>

      <!-- 右侧编辑器 -->
      <main class="type-editor" v-if="currentType">
        <p class="editor-note">{{ typeForm.desc || '请填写合同类型描述' }}</p>
        <div class="editor-grid">
          <div class="field">
            <label>合同类型名称 <span class="req">*</span></label>
            <el-input v-model="typeForm.name" placeholder="请输入合同类型名称" />
          </div>
          <div class="field">
            <label>合同立场 <span class="req">*</span></label>
            <el-select v-model="typeForm.stance" class="full">
              <el-option label="甲方" value="甲方" />
              <el-option label="乙方" value="乙方" />
            </el-select>
          </div>
          <div class="field wide">
            <label>描述</label>
            <el-input v-model="typeForm.desc" placeholder="请输入合同类型描述" />
          </div>
        </div>

        <!-- 审查点选择 -->
        <section class="audit-select">
          <div class="audit-head">
            <div><h3>审查点选择</h3><p>已选 {{ assocSelected.length }} 个，共 {{ points.length }} 个可用审查点</p></div>
            <el-button @click="assocSelected = []">清空已选</el-button>
          </div>
          <div class="audit-filters">
            <el-input v-model="auditKw" placeholder="搜索审查点名称" clearable size="small" style="width:200px" />
            <el-select v-model="auditDim" clearable placeholder="全部维度" size="small" style="width:140px">
              <el-option v-for="dim in allDims" :key="dim" :label="dim" :value="dim" />
            </el-select>
          </div>
          <div v-loading="loadingAssoc">
            <div v-for="(group, dim) in filteredPointsByDim" :key="dim" class="audit-group">
              <h4>{{ dim }}</h4>
              <label v-for="p in group" :key="p.id" class="audit-option">
                <el-checkbox :model-value="assocSelected.includes(p.id)" @change="toggleAssoc(p.id)" />
                <span><b>{{ p.name }}</b><small>{{ p.desc }}</small></span>
              </label>
            </div>
            <div v-if="!Object.keys(filteredPointsByDim).length" class="audit-empty">无匹配审查点</div>
          </div>
        </section>

        <div class="editor-actions">
          <el-button type="danger" plain @click="deleteCurrentType">删除该合同类型</el-button>
          <div style="display:flex;gap:10px">
            <el-button @click="cancelEdit">取消</el-button>
            <el-button type="primary" :loading="savingType" @click="saveTypeConfig">确认保存</el-button>
          </div>
        </div>
      </main>
      <main class="type-editor type-empty" v-else>
        <p>从左侧选择合同类型，或新建</p>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppTopbar from '../../components/AppTopbar.vue'
import { listPoints, savePoint } from '../../services/point.service'
import { listTypes, saveType, deleteType, getType, saveAuditPoints } from '../../services/type.service'

const router = useRouter()
const tab = ref('points')

// ===== 审核点 Tab =====
const points = ref([])
const loadingPoints = ref(false)
const pointKw = ref('')

onMounted(() => { loadPoints(); loadTypes() })

async function loadPoints() {
  loadingPoints.value = true
  try { const { items } = await listPoints({ keyword: pointKw.value }); points.value = items }
  finally { loadingPoints.value = false }
}
async function togglePoint(row, v) {
  await savePoint({ id: row.id, status: v ? '已启用' : '已停用' })
  row.status = v ? '已启用' : '已停用'
  ElMessage.success('状态已更新')
}

// ===== 合同类型 Tab =====
const types = ref([])
const loadingTypes = ref(false)
const currentType = ref(null)
const savingType = ref(false)
const loadingAssoc = ref(false)

const typeForm = reactive({ id: '', name: '', stance: '甲方', desc: '', keywords: [] })
const assocSelected = ref([])

const auditKw = ref('')
const auditDim = ref('')

// 审核点按维度分组（全量，用于维度下拉）
const pointsByDim = computed(() => {
  const map = {}
  for (const p of points.value) {
    const dim = p.dimension || '其他'
    if (!map[dim]) map[dim] = []
    map[dim].push(p)
  }
  return map
})

const allDims = computed(() => Object.keys(pointsByDim.value))

// 过滤后按维度分组
const filteredPointsByDim = computed(() => {
  const map = {}
  for (const p of points.value) {
    if (auditDim.value && p.dimension !== auditDim.value) continue
    if (auditKw.value && !p.name.includes(auditKw.value)) continue
    const dim = p.dimension || '其他'
    if (!map[dim]) map[dim] = []
    map[dim].push(p)
  }
  return map
})

async function loadTypes() {
  loadingTypes.value = true
  try { const { items } = await listTypes(); types.value = items }
  finally { loadingTypes.value = false }
}

async function selectType(t) {
  currentType.value = t
  Object.assign(typeForm, { id: t.id, name: t.name, stance: t.stance, desc: t.desc || t.description || '', keywords: Array.isArray(t.keywords) ? [...t.keywords] : [] })
  loadingAssoc.value = true
  try {
    const detail = await getType(t.id)
    assocSelected.value = (detail?.linkedAuditPoints || []).filter(x => x.enabled).map(x => x.auditPointId)
  } finally { loadingAssoc.value = false }
  // 确保审核点已加载
  if (!points.value.length) await loadPoints()
}

function newType() {
  currentType.value = { id: null }
  Object.assign(typeForm, { id: '', name: '', stance: '甲方', desc: '', keywords: [] })
  assocSelected.value = []
  if (!points.value.length) loadPoints()
}

function cancelEdit() {
  currentType.value = null
}

function toggleAssoc(id) {
  const i = assocSelected.value.indexOf(id)
  if (i > -1) assocSelected.value.splice(i, 1)
  else assocSelected.value.push(id)
}

async function saveTypeConfig() {
  if (!typeForm.name || !typeForm.stance) {
    ElMessage.warning('请填写合同类型名称和立场')
    return
  }
  savingType.value = true
  try {
    const res = await saveType({ id: typeForm.id || undefined, name: typeForm.name, stance: typeForm.stance, desc: typeForm.desc, keywords: typeForm.keywords })
    const savedId = typeForm.id || res?.data?.id
    if (savedId) await saveAuditPoints(savedId, assocSelected.value)
    ElMessage.success('保存成功')
    await loadTypes()
    // 重新选中已保存的类型
    const found = types.value.find(t => t.name === typeForm.name && t.stance === typeForm.stance)
    if (found) selectType(found)
  } finally {
    savingType.value = false
  }
}

async function deleteCurrentType() {
  if (!typeForm.id) { currentType.value = null; return }
  await ElMessageBox.confirm(`确认删除合同类型「${typeForm.name}」？`, '提示', { type: 'warning' })
  await deleteType(typeForm.id)
  ElMessage.success('已删除')
  currentType.value = null
  await loadTypes()
}
</script>

<style scoped>
.page { flex: 1; padding: 20px 28px 30px; overflow: auto; }
.cfg-tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 0.667px solid var(--line); }
.cfg-tab { border: 0; background: transparent; padding: 10px 4px; margin-right: 18px; font-size: 15px; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.cfg-tab.on { color: var(--blue); font-weight: 600; border-bottom-color: var(--blue); }
.head { display: flex; align-items: flex-start; justify-content: space-between; }
.head h1 { margin: 0; font-size: 22px; font-weight: 700; }
.head p { margin: 8px 0 0; color: var(--muted); }
.head-actions { display: flex; gap: 10px; }
.search { display: flex; gap: 10px; align-items: center; margin: 18px 0 16px; }
.search .el-input { max-width: 320px; }
.pager { padding: 14px 16px; color: var(--muted); font-size: 13px; }

/* 合同类型分栏 */
.type-shell { display: grid; grid-template-columns: 240px 1fr; min-height: 600px; border: 0.667px solid var(--line); border-radius: 14px; background: #fff; overflow: hidden; }
.type-aside { border-right: 0.667px solid #e0e6ef; background: #fbfcff; display: flex; flex-direction: column; }
.type-aside-title { padding: 16px 18px; font-weight: 700; border-bottom: 0.667px solid #e7ecf4; font-size: 13.5px; }
.type-list { flex: 1; display: flex; flex-direction: column; gap: 8px; padding: 12px; overflow-y: auto; }
.type-item { padding: 12px 14px; border: 1px solid transparent; border-radius: 10px; cursor: pointer; }
.type-item:hover { background: #f5f6ff; }
.type-item.on { border-color: #e1e5ff; background: #f0f2ff; }
.type-item b { display: block; font-size: 14px; }
.type-item span { display: block; margin-top: 4px; color: #8a96aa; font-size: 12px; }
.dot { display: inline-block; width: 8px; height: 8px; margin-right: 7px; border-radius: 50%; }
.type-add { margin: 12px; border-top: 0.667px solid #e7ecf4; padding-top: 12px; }
.type-editor { padding: 26px 30px; overflow-y: auto; }
.type-empty { display: flex; align-items: center; justify-content: center; color: var(--muted); }
.editor-note { margin: 0 0 20px; padding-bottom: 16px; border-bottom: 0.667px solid #e7ecf4; color: #7b879a; font-weight: 600; font-size: 13px; }
.editor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.field { margin-bottom: 4px; }
.field.wide { grid-column: 1 / -1; }
.field label { display: block; margin-bottom: 8px; font-size: 13px; color: #526077; }
.req { color: var(--red); }
.full { width: 100%; }
.audit-select { margin-top: 26px; }
.audit-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 14px; }
.audit-head h3 { margin: 0 0 4px; font-size: 15px; }
.audit-head p { margin: 0; color: var(--muted); font-size: 13px; }
.audit-filters { display: flex; gap: 10px; margin-bottom: 12px; }
.audit-empty { padding: 24px; text-align: center; color: var(--muted); font-size: 13px; }

.audit-group h4 { margin: 0 0 10px; color: #5e6b82; font-size: 13px; }
.audit-option { display: flex; align-items: flex-start; gap: 10px; width: min(650px, 100%); padding: 12px 14px; margin: 6px 0; border: 0.667px solid #e0e6ef; border-radius: 10px; cursor: pointer; }
.audit-option b { display: block; font-size: 13.5px; }
.audit-option small { display: block; margin-top: 3px; color: #8a96aa; font-size: 12px; }
.editor-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 26px; padding-top: 20px; border-top: 0.667px solid #e7ecf4; }
</style>
