<template>
  <AppTopbar title="配置中心 · 审核风险点定义">
    <template #actions>
      <el-button @click="router.push({ name: 'config' })">返回审核点管理</el-button>
    </template>
  </AppTopbar>

  <div class="page" v-loading="loading">
    <div class="page-head">
      <h1>审核风险点定义</h1>
      <p>定义风险点信息、缺省审查结果与审查示例，保存后返回审核点首页。</p>
    </div>

    <!-- 基本信息 -->
    <section class="card">
      <div class="grid2">
        <div class="field">
          <label>审核点名称 *</label>
          <el-input v-model="form.name" placeholder="如：默示验收风险" />
        </div>
        <div class="field">
          <label>审核维度</label>
          <el-select v-model="form.dimId" class="full" placeholder="请选择维度" @change="onDimChange">
            <el-option v-for="d in dims" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </div>
        <div class="field">
          <label>审查点说明</label>
          <el-input v-model="form.note" type="textarea" :rows="3" />
        </div>
        <div class="field">
          <label>审查点描述</label>
          <el-input v-model="form.desc" type="textarea" :rows="3" />
        </div>
      </div>
    </section>

    <!-- 风险点信息 -->
    <section class="card">
      <div class="sec-head">
        <div>
          <h2>审查点风险点信息</h2>
          <p>一个审查点可配置多条风险点及其等级判定条件</p>
        </div>
        <el-button circle @click="addRisk"><el-icon><Plus /></el-icon></el-button>
      </div>

      <div v-for="(r, i) in form.risks" :key="i" class="sub-card">
        <div class="sub-head">
          <b>风险点 {{ cn(i + 1) }}</b>
          <el-button size="small" type="danger" plain @click="form.risks.splice(i, 1)">删除</el-button>
        </div>
        <div class="field"><label>风险点名称</label><el-input v-model="r.title" /></div>
        <div class="field"><label>高风险说明</label><el-input v-model="r.high" type="textarea" :rows="3" /></div>
        <div class="field"><label>低风险说明</label><el-input v-model="r.low" type="textarea" :rows="3" /></div>
        <div class="field"><label>无风险说明</label><el-input v-model="r.noneStd" type="textarea" :rows="3" /></div>
      </div>
    </section>

    <!-- 缺省审查结果 -->
    <section class="card">
      <div class="sec-head">
        <div>
          <h2>缺省审查结果</h2>
          <p>未单独配置结果时，系统默认返回以下审查结论</p>
        </div>
      </div>
      <div class="field">
        <label>风险等级</label>
        <el-select v-model="form.def.level" class="full">
          <el-option label="高风险" value="高风险" />
          <el-option label="低风险" value="低风险" />
          <el-option label="无风险" value="无风险" />
        </el-select>
      </div>
      <template v-if="form.def.level !== '无风险'">
        <div class="field">
          <label>风险点</label>
          <el-select v-model="form.def.riskPointName" class="full" clearable placeholder="选择关联风险点">
            <el-option v-for="r in form.risks" :key="r.title" :label="r.title" :value="r.title" />
          </el-select>
        </div>
      </template>
      <div class="field"><label>风险分析</label><el-input v-model="form.def.overview" type="textarea" :rows="2" /></div>
      <div v-if="form.def.level !== '无风险'" class="field">
        <label>修改建议</label><el-input v-model="form.def.solution" type="textarea" :rows="2" />
      </div>
    </section>

    <!-- 审查示例 -->
    <section class="card">
      <div class="sec-head">
        <div><h2>审查示例</h2></div>
        <el-button circle @click="addExample"><el-icon><Plus /></el-icon></el-button>
      </div>
      <div v-for="(ex, i) in form.examples" :key="i" class="sub-card">
        <div class="sub-head">
          <b>示例{{ cn(i + 1) }}</b>
          <el-button size="small" type="danger" plain @click="form.examples.splice(i, 1)">删除</el-button>
        </div>
        <div class="field"><label>合同原文</label><el-input v-model="ex.clause" type="textarea" :rows="2" /></div>
        <div class="field">
          <label>风险等级</label>
          <el-select v-model="ex.level" class="full">
            <el-option label="高风险" value="高风险" />
            <el-option label="低风险" value="低风险" />
            <el-option label="无风险" value="无风险" />
          </el-select>
        </div>
        <template v-if="ex.level !== '无风险'">
          <div class="field">
            <label>风险点</label>
            <el-select v-model="ex.riskPointName" class="full" clearable placeholder="选择关联风险点">
              <el-option v-for="r in form.risks" :key="r.title" :label="r.title" :value="r.title" />
            </el-select>
          </div>
        </template>
        <div class="field"><label>风险分析</label><el-input v-model="ex.overview" type="textarea" :rows="2" /></div>
        <div v-if="ex.level !== '无风险'" class="field">
          <label>修改建议</label><el-input v-model="ex.solution" type="textarea" :rows="2" />
        </div>
      </div>
    </section>

    <div class="actions">
      <el-button @click="router.push({ name: 'config' })">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import AppTopbar from '../../components/AppTopbar.vue'
import { getPoint, savePoint, listDimensions } from '../../services/point.service'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.params.id === 'new')
const loading = ref(false)
const saving = ref(false)
const dims = ref([])
const form = reactive({
  id: '',
  name: '',
  dimension: '',
  dimId: null,
  note: '',
  desc: '',
  risks: [{ title: '', high: '', low: '', noneStd: '' }],
  def: { level: '高风险', riskPointName: '', overview: '', solution: '' },
  examples: [{ clause: '', level: '高风险', riskPointName: '', overview: '', solution: '' }],
})

const cnNums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
const cn = (n) => cnNums[n - 1] || n

function onDimChange(id) {
  const d = dims.value.find((x) => x.id === id)
  form.dimension = d ? d.name : ''
}

onMounted(async () => {
  dims.value = await listDimensions()
  if (!isNew.value) {
    loading.value = true
    try {
      const p = await getPoint(route.params.id)
      if (p) {
        Object.assign(form, {
          id: p.id,
          name: p.name,
          dimId: p.dimId,
          dimension: p.dimension,
          desc: p.desc,
          note: p.instruction,
        })
        if (Array.isArray(p.risks) && p.risks.length) {
          form.risks = p.risks.map((r) => ({
            title: r.name || r.title || '',
            high: r.highStd || r.high || '',
            low: r.lowStd || r.low || '',
            noneStd: r.noneStd || '',
          }))
        }
        if (p.defaultResult) {
          form.def = {
            level: p.defaultResult.level || '高风险',
            riskPointName: p.defaultResult.riskPointName || '',
            overview: p.defaultResult.analysis || p.defaultResult.overview || '',
            solution: p.defaultResult.suggestion || p.defaultResult.solution || '',
          }
        }
        if (Array.isArray(p.examples) && p.examples.length) {
          form.examples = p.examples.map((ex) => ({
            clause: ex.original || ex.clause || '',
            level: ex.level || '高风险',
            riskPointName: ex.riskPointName || '',
            overview: ex.analysis || ex.overview || '',
            solution: ex.suggestion || ex.solution || '',
          }))
        }
      }
    } finally {
      loading.value = false
    }
  }
})

function addRisk() {
  form.risks.push({ title: '', high: '', low: '', noneStd: '' })
}
function addExample() {
  form.examples.push({ clause: '', level: '高风险', overview: '', solution: '' })
}

async function save() {
  if (!form.name) {
    ElMessage.warning('请填写审核点名称')
    return
  }
  saving.value = true
  try {
    await savePoint({
      id: isNew.value ? undefined : form.id,
      name: form.name,
      dimId: form.dimId,
      dimension: form.dimension,
      desc: form.desc,
      instruction: form.note,
      risks: form.risks.map((r) => ({
        name: r.title,
        highStd: r.high,
        lowStd: r.low,
        noneStd: r.noneStd,
      })),
      defaultResult: {
        level: form.def.level,
        riskPointName: form.def.level !== '无风险' ? form.def.riskPointName : '',
        analysis: form.def.overview,
        suggestion: form.def.level !== '无风险' ? form.def.solution : '',
      },
      examples: form.examples.map((ex) => ({
        original: ex.clause,
        level: ex.level,
        riskPointName: ex.level !== '无风险' ? ex.riskPointName : '',
        analysis: ex.overview,
        suggestion: ex.level !== '无风险' ? ex.solution : '',
      })),
    })
    ElMessage.success('保存成功')
    router.push({ name: 'config' })
  } finally {
    saving.value = false
  }
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
  margin: 8px 0 18px;
  color: var(--muted);
}
.card {
  background: #fff;
  border: 0.667px solid var(--line);
  border-radius: 14px;
  padding: 22px;
  margin-bottom: 18px;
}
.sec-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.sec-head h2 {
  margin: 0 0 4px;
  font-size: 16px;
}
.sec-head p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.field {
  margin-bottom: 16px;
}
.field:last-child {
  margin-bottom: 0;
}
.field label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #526077;
}
.full {
  width: 100%;
}
.sub-card {
  border: 0.667px solid var(--line);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
  background: #fafbfe;
}
.sub-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-bottom: 30px;
}
</style>
