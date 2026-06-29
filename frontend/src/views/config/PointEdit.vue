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
          <el-select v-model="form.dimension" class="full" placeholder="请选择维度">
            <el-option v-for="d in dims" :key="d" :label="d" :value="d" />
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
        <div class="field"><label>条文说明</label><el-input v-model="r.clauseNote" /></div>
        <div class="field"><label>低风险说明</label><el-input v-model="r.low" /></div>
        <div class="field"><label>高风险说明</label><el-input v-model="r.high" /></div>
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
      <div class="field"><label>合同原文</label><el-input v-model="form.def.clause" type="textarea" :rows="2" /></div>
      <div class="field"><label>风险模型</label><el-input v-model="form.def.model" type="textarea" :rows="2" /></div>
      <div class="field"><label>风险说明</label><el-input v-model="form.def.overview" type="textarea" :rows="2" /></div>
      <div class="field"><label>修改建议</label><el-input v-model="form.def.solution" type="textarea" :rows="2" /></div>
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
        <div class="field"><label>风险模型</label><el-input v-model="ex.model" type="textarea" :rows="2" /></div>
        <div class="field"><label>风险说明</label><el-input v-model="ex.overview" type="textarea" :rows="2" /></div>
        <div class="field"><label>修改建议</label><el-input v-model="ex.solution" type="textarea" :rows="2" /></div>
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
  note: '',
  desc: '',
  risks: [{ title: '', clauseNote: '', low: '', high: '' }],
  def: { clause: '', model: '', overview: '', solution: '' },
  examples: [{ clause: '', model: '', overview: '', solution: '' }],
})

const cnNums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
const cn = (n) => cnNums[n - 1] || n

onMounted(async () => {
  dims.value = await listDimensions()
  if (!isNew.value) {
    loading.value = true
    try {
      const p = await getPoint(route.params.id)
      if (p) {
        form.id = p.id
        form.name = p.name || ''
        form.dimension = p.dimension || ''
        form.note = p.note || ''
        form.desc = p.desc || ''
        if (p.risks && p.risks.length) {
          form.risks = p.risks
        }
        if (p.def) {
          form.def.clause = p.def.clause || ''
          form.def.model = p.def.model || ''
          form.def.overview = p.def.overview || ''
          form.def.solution = p.def.solution || ''
        }
        if (p.examples && p.examples.length) {
          form.examples = p.examples
        }
      }
    } finally {
      loading.value = false
    }
  }
})

function addRisk() {
  form.risks.push({ title: '', clauseNote: '', low: '', high: '' })
}
function addExample() {
  form.examples.push({ clause: '', model: '', overview: '', solution: '' })
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
      dimension: form.dimension,
      note: form.note,
      desc: form.desc,
      risks: form.risks.filter((r) => r.title),
      def: form.def,
      examples: form.examples.filter((e) => e.clause || e.overview || e.solution),
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
