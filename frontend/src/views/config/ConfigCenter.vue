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

    <!-- 合同类型管理 -->
    <section v-show="tab === 'types'">
      <div class="head">
        <div>
          <h1>合同类型管理</h1>
          <p>维护合同类型名称、合同立场、合同描述与关键信息识别范围</p>
        </div>
        <el-button type="primary" @click="router.push({ name: 'contractTypeNew' })">＋ 新建合同类型</el-button>
      </div>

      <div class="info-banner">
        大模型依据合同类型名称、合同描述进行自动识别；合同类型与审核风险点解耦管理，互不强绑定。
      </div>

      <div class="stats">
        <div class="stat"><span>合同类型</span><b>{{ types.length }}</b></div>
        <div class="stat"><span>已启用</span><b>{{ enabledTypeCount }}</b></div>
      </div>

      <el-card shadow="never" body-style="padding:0">
        <el-table :data="types" v-loading="loadingTypes">
          <el-table-column prop="name" label="合同类型" width="150" />
          <el-table-column prop="stance" label="合同立场" width="100" />
          <el-table-column prop="desc" label="合同描述" min-width="280" show-overflow-tooltip />
          <el-table-column label="关联审查点" width="110">
            <template #default="{ row }">{{ row.relatedPoints }} 个</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-switch :model-value="row.status === '已启用'" @change="(v) => toggleType(row, v)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push({ name: 'contractTypeEdit', params: { id: row.id } })">编辑</el-button>
              <el-button link @click="openAssociation(row)">关联审核点</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <!-- 关联审核点弹层 -->
    <el-dialog v-model="assocDialog" :title="`关联审核点 · ${assocType?.name || ''}`" width="560px">
      <p class="dlg-sub">勾选该合同类型默认推荐的审核点；用户发起审核时仍可自由增减。</p>
      <div class="assoc-list" v-loading="loadingAssoc">
        <label v-for="p in points" :key="p.id" class="assoc-item">
          <el-checkbox :model-value="assocSelected.includes(String(p.id))" @change="() => toggleAssoc(String(p.id))" />
          <div>
            <b>{{ p.name }}</b>
            <small>{{ p.dimension }} · {{ p.desc }}</small>
          </div>
        </label>
      </div>
      <template #footer>
        <el-button @click="assocDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAssociation">保存关联（已选 {{ assocSelected.length }}）</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppTopbar from '../../components/AppTopbar.vue'
import { listPoints, savePoint } from '../../services/point.service'
import { getType, listTypes, saveAuditPoints, saveType } from '../../services/type.service'

const route = useRoute()
const router = useRouter()
const tab = ref(route.query.tab === 'types' ? 'types' : 'points')

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
const enabledTypeCount = computed(() => types.value.filter((t) => t.status === '已启用').length)

async function loadTypes() {
  loadingTypes.value = true
  try { const { items } = await listTypes(); types.value = items }
  finally { loadingTypes.value = false }
}

async function toggleType(row, v) {
  await saveType({ id: row.id, status: v ? '已启用' : '已停用' })
  row.status = v ? '已启用' : '已停用'
  ElMessage.success('状态已更新')
}

// ===== 关联审核点弹层 =====
const assocDialog = ref(false)
const assocType = ref(null)
const assocSelected = ref([])
const loadingAssoc = ref(false)

async function openAssociation(row) {
  assocType.value = row
  assocSelected.value = []
  assocDialog.value = true
  loadingAssoc.value = true
  try {
    if (!points.value.length) await loadPoints()
    const detail = await getType(row.id)
    const linked = detail?.linkedAuditPoints || []
    assocSelected.value = linked.length
      ? linked.filter((item) => item.enabled).map((item) => String(item.auditPointId))
      : points.value.slice(0, row.relatedPoints || 0).map((point) => String(point.id))
  } finally {
    loadingAssoc.value = false
  }
}

function toggleAssoc(id) {
  const i = assocSelected.value.indexOf(id)
  if (i > -1) assocSelected.value.splice(i, 1)
  else assocSelected.value.push(id)
}

async function saveAssociation() {
  if (assocType.value) {
    await saveAuditPoints(assocType.value.id, assocSelected.value)
    assocType.value.relatedPoints = assocSelected.value.length
  }
  assocDialog.value = false
  ElMessage.success('审核点与合同类型关联已保存')
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
.info-banner {
  margin: 18px 0;
  padding: 14px 16px;
  background: #eef1fe;
  border: 0.667px solid #d7ddfb;
  border-radius: 10px;
  color: #4658c4;
  font-size: 13.5px;
}
.stats { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 18px; }
.stat {
  background: #fff; border: 0.667px solid var(--line); border-radius: 12px;
  padding: 16px 20px; display: flex; flex-direction: column; gap: 6px;
}
.stat span { font-size: 13px; color: var(--muted); }
.stat b { font-size: 22px; }
.dlg-sub { margin: 0 0 18px; color: var(--muted); font-size: 13px; }
.assoc-list { max-height: 360px; overflow: auto; display: flex; flex-direction: column; gap: 8px; }
.assoc-item {
  display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px;
  border: 0.667px solid var(--line); border-radius: 10px; cursor: pointer;
}
.assoc-item b { display: block; font-size: 14px; color: var(--ink); }
.assoc-item small { color: var(--muted); font-size: 12px; }
</style>
