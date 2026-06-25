<template>
  <AppTopbar title="配置中心" />

  <div class="page">
    <!-- 一级 Tab：审核点管理 / 合同类型管理 -->
    <div class="cfg-tabs">
      <button class="cfg-tab" :class="{ on: tab === 'points' }" @click="tab = 'points'">
        审核点管理
      </button>
      <button class="cfg-tab" :class="{ on: tab === 'types' }" @click="tab = 'types'">
        合同类型管理
      </button>
    </div>

    <!-- 审核点管理 -->
    <section v-show="tab === 'points'">
      <div class="head">
        <div>
          <h1>审核点管理</h1>
          <p>统一维护审核点及其风险点信息</p>
        </div>
        <div class="head-actions">
          <el-button @click="router.push({ name: 'configDimensions' })">维度管理</el-button>
          <el-button type="primary" @click="router.push({ name: 'pointEdit', params: { id: 'new' } })">
            ＋ 新建审核点
          </el-button>
        </div>
      </div>

      <div class="search">
        <el-input v-model="pointKw" placeholder="搜索审核点名称" clearable @keyup.enter="loadPoints" />
        <el-button type="primary" @click="loadPoints">检索</el-button>
        <el-button @click="((pointKw = ''), loadPoints())">重置</el-button>
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
              <el-button link type="primary" @click="router.push({ name: 'pointEdit', params: { id: row.id } })">
                编辑
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager">
          <span>共 {{ points.length }} 个审核点</span>
        </div>
      </el-card>
    </section>

    <!-- 合同类型管理 -->
    <section v-show="tab === 'types'">
      <div class="head">
        <div>
          <h1>合同类型管理</h1>
          <p>维护合同类型名称、合同立场、合同描述与关键信息识别范围</p>
        </div>
        <el-button type="primary" @click="openTypeConfig(null)">＋ 新建合同类型</el-button>
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
          <el-table-column prop="desc" label="合同描述" min-width="280" show-overflow-tooltip />
          <el-table-column label="状态" width="150">
            <template #default="{ row }">
              <el-switch :model-value="row.status === '已启用'" @change="(v) => toggleType(row, v)" />
              <span class="status-text">{{ row.status }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openTypeConfig(row)">配置</el-button>
              <el-button link @click="openAssociation(row)">关联审核点</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>
  </div>

  <!-- 合同类型配置弹层 -->
  <el-dialog v-model="typeDialog" :title="typeForm.id ? '编辑合同类型' : '新建合同类型'" width="640px">
    <p class="dlg-sub">定义合同类型、审核立场及合同关键信息识别范围。</p>
    <div class="dlg-grid">
      <div class="field">
        <label>合同类型 <span class="req">*</span></label>
        <el-input v-model="typeForm.name" placeholder="请输入合同类型名称" />
      </div>
      <div class="field">
        <label>合同立场 <span class="req">*</span></label>
        <el-select v-model="typeForm.stance" class="full">
          <el-option label="甲方立场" value="甲方立场" />
          <el-option label="乙方立场" value="乙方立场" />
        </el-select>
      </div>
      <div class="field wide">
        <label>合同描述</label>
        <el-input v-model="typeForm.desc" type="textarea" :rows="2" placeholder="请输入该合同类型的定义、适用范围及主要业务特征" />
      </div>
    </div>

    <div class="key-card">
      <label class="key-title">
        <el-checkbox v-model="typeForm.subjectInfo">选择主体信息</el-checkbox>
        <span class="key-hint">同时识别甲方、乙方</span>
      </label>
      <div class="party" :class="{ off: !typeForm.subjectInfo }">
        <div><b>甲方主体信息</b><p>主体名称：华城数字建设有限公司</p><p>主体角色：采购方 / 委托方</p></div>
        <div><b>乙方主体信息</b><p>主体名称：云启科技有限公司</p><p>主体角色：供应方 / 承接方</p></div>
      </div>
    </div>

    <div class="key-card">
      <label class="key-title">
        <el-checkbox v-model="typeForm.subjectMatter">标的物</el-checkbox>
        <span class="key-hint">勾选后识别标的物</span>
      </label>
      <div class="field">
        <label>标的物名称</label>
        <el-input v-model="typeForm.subjectMatterName" :disabled="!typeForm.subjectMatter" />
      </div>
    </div>

    <template #footer>
      <el-button @click="typeDialog = false">取消</el-button>
      <el-button type="primary" :loading="savingType" @click="saveTypeConfig">保存</el-button>
    </template>
  </el-dialog>

  <!-- 关联审核点弹层 -->
  <el-dialog v-model="assocDialog" :title="`关联审核点 · ${assocType?.name || ''}`" width="560px">
    <p class="dlg-sub">勾选该合同类型默认推荐的审核点；用户发起审核时仍可自由增减。</p>
    <div class="assoc-list">
      <label v-for="p in points" :key="p.id" class="assoc-item">
        <el-checkbox :model-value="assocSelected.includes(p.id)" @change="() => toggleAssoc(p.id)" />
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
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppTopbar from '../../components/AppTopbar.vue'
import { listPoints, savePoint } from '../../services/point.service'
import { listTypes, saveType } from '../../services/type.service'

const router = useRouter()
const tab = ref('points')

const points = ref([])
const loadingPoints = ref(false)
const pointKw = ref('')

const types = ref([])
const loadingTypes = ref(false)
const enabledTypeCount = computed(() => types.value.filter((t) => t.status === '已启用').length)

onMounted(() => {
  loadPoints()
  loadTypes()
})

async function loadPoints() {
  loadingPoints.value = true
  try {
    const { items } = await listPoints({ keyword: pointKw.value })
    points.value = items
  } finally {
    loadingPoints.value = false
  }
}
async function loadTypes() {
  loadingTypes.value = true
  try {
    const { items } = await listTypes()
    types.value = items
  } finally {
    loadingTypes.value = false
  }
}
async function togglePoint(row, v) {
  await savePoint({ id: row.id, status: v ? '已启用' : '已停用' })
  row.status = v ? '已启用' : '已停用'
  ElMessage.success('状态已更新')
}
async function toggleType(row, v) {
  await saveType({ id: row.id, status: v ? '已启用' : '已停用' })
  row.status = v ? '已启用' : '已停用'
  ElMessage.success('状态已更新')
}

// ===== 合同类型配置弹层 =====
const typeDialog = ref(false)
const savingType = ref(false)
const typeForm = reactive({
  id: '',
  name: '',
  stance: '甲方立场',
  desc: '',
  subjectInfo: true,
  subjectMatter: true,
  subjectMatterName: '',
})

function openTypeConfig(row) {
  Object.assign(typeForm, {
    id: row?.id || '',
    name: row?.name || '',
    stance: row?.stance || '甲方立场',
    desc: row?.desc || '',
    subjectInfo: true,
    subjectMatter: true,
    subjectMatterName: row?.name === '采购合同' ? '智慧园区软件系统采购及实施服务' : '',
  })
  typeDialog.value = true
}
async function saveTypeConfig() {
  if (!typeForm.name) {
    ElMessage.warning('请填写合同类型名称')
    return
  }
  savingType.value = true
  try {
    await saveType({
      id: typeForm.id || undefined,
      name: typeForm.name,
      stance: typeForm.stance,
      desc: typeForm.desc,
    })
    ElMessage.success('保存成功')
    typeDialog.value = false
    loadTypes()
  } finally {
    savingType.value = false
  }
}

// ===== 关联审核点弹层 =====
const assocDialog = ref(false)
const assocType = ref(null)
const assocSelected = ref([])

function openAssociation(row) {
  assocType.value = row
  assocSelected.value = points.value.slice(0, row.relatedPoints || 0).map((p) => p.id)
  assocDialog.value = true
}
function toggleAssoc(id) {
  const i = assocSelected.value.indexOf(id)
  if (i > -1) assocSelected.value.splice(i, 1)
  else assocSelected.value.push(id)
}
async function saveAssociation() {
  if (assocType.value) {
    await saveType({ id: assocType.value.id, relatedPoints: assocSelected.value.length })
    assocType.value.relatedPoints = assocSelected.value.length
  }
  assocDialog.value = false
  ElMessage.success('审核点与合同类型关联已保存')
}
</script>

<style scoped>
.page {
  flex: 1;
  padding: 20px 28px 30px;
  overflow: auto;
}
.cfg-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 0.667px solid var(--line);
}
.cfg-tab {
  border: 0;
  background: transparent;
  padding: 10px 4px;
  margin-right: 18px;
  font-size: 15px;
  color: var(--muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.cfg-tab.on {
  color: var(--blue);
  font-weight: 600;
  border-bottom-color: var(--blue);
}
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.head h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.head p {
  margin: 8px 0 0;
  color: var(--muted);
}
.head-actions {
  display: flex;
  gap: 10px;
}
.search {
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 18px 0 16px;
}
.search .el-input {
  max-width: 320px;
}
.pager {
  padding: 14px 16px;
  color: var(--muted);
  font-size: 13px;
}
.info-banner {
  margin: 18px 0;
  padding: 14px 16px;
  background: #eef1fe;
  border: 0.667px solid #d7ddfb;
  border-radius: 10px;
  color: #4658c4;
  font-size: 13.5px;
}
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 18px;
}
.stat {
  background: #fff;
  border: 0.667px solid var(--line);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.stat span {
  font-size: 13px;
  color: var(--muted);
}
.stat b {
  font-size: 22px;
}
.status-text {
  margin-left: 8px;
  font-size: 13px;
  color: var(--muted);
}
.dlg-sub {
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 13px;
}
.dlg-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
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
.key-card {
  border: 0.667px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
  margin-top: 16px;
  background: #fafbfe;
}
.key-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.key-hint {
  font-size: 12px;
  color: var(--muted);
}
.party {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  transition: opacity 0.15s;
}
.party.off {
  opacity: 0.42;
}
.party b {
  font-size: 13.5px;
}
.party p {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: var(--muted);
}
.assoc-list {
  max-height: 360px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.assoc-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 0.667px solid var(--line);
  border-radius: 10px;
  cursor: pointer;
}
.assoc-item b {
  display: block;
  font-size: 14px;
  color: var(--ink);
}
.assoc-item small {
  color: var(--muted);
  font-size: 12px;
}
</style>
