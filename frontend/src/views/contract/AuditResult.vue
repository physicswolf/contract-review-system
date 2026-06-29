<template>
  <AppTopbar :title="data?.contractName || '审核结果'">
    <template #actions>
      <el-button @click="router.push({ name: 'contracts' })">返回列表</el-button>
      <el-button type="primary" @click="onExport">导出审核意见</el-button>
    </template>
  </AppTopbar>

  <div class="result" v-loading="loading">
    <!-- 左：合同原文 -->
    <section class="pane original">
      <div class="pane-head">
        <span class="doc-badge">{{ data?.docType || 'Word' }}</span>
        <span class="pane-title">原文</span>
      </div>
      <div class="doc">
        <template v-for="(b, i) in data?.originalText || []" :key="i">
          <h2 v-if="b.type === 'h2'">{{ b.text }}</h2>
          <h3 v-else-if="b.type === 'h3'">{{ b.text }}</h3>
          <p v-else-if="b.type === 'highlight'" class="hl">{{ b.text }}</p>
          <p v-else>{{ b.text }}</p>
        </template>
      </div>
    </section>

    <!-- 右：审查结果 -->
    <section class="pane review">
      <div class="pane-head">
        <span class="pane-title">审查结果</span>
      </div>

      <div class="dim-tabs">
        <button
          v-for="d in dimTabs"
          :key="d"
          class="dim-tab"
          :class="{ on: activeDim === d }"
          @click="activeDim = d"
        >
          {{ d }}
        </button>
      </div>

      <div class="level-pills">
        <button class="pill" :class="{ on: levelFilter === 'all' }" @click="levelFilter = 'all'">
          全部 ({{ total }})
        </button>
        <button class="pill red" :class="{ on: levelFilter === 'major' }" @click="levelFilter = 'major'">
          重大风险 ({{ majorCount }})
        </button>
        <button class="pill amber" :class="{ on: levelFilter === 'general' }" @click="levelFilter = 'general'">
          一般风险 ({{ generalCount }})
        </button>
      </div>

      <div class="cards">
        <section v-for="g in groups" :key="g.dimension" class="dim-group">
          <div class="dim-group-head">
            <span class="dim-group-name">{{ g.dimension }}</span>
            <span class="dim-group-count">{{ g.risks.length }} 条</span>
          </div>

          <div v-for="(r, i) in g.risks" :key="i" class="risk-card">
            <div class="rc-head">
              <span class="rc-no">风险点 {{ i + 1 }}</span>
              <b class="rc-title">{{ r.title }}</b>
              <RiskTag
                :level="r.level === 'major' ? 'major' : 'general'"
                :text="r.level === 'major' ? '重大风险' : '一般风险'"
              />
            </div>

            <div class="rc-section">
              <label>风险说明</label>
              <p>{{ r.desc }}</p>
            </div>
            <div class="rc-section">
              <label>风险分析</label>
              <p>{{ r.analysis }}</p>
            </div>
            <div class="rc-section">
              <label>修改示例</label>
              <div class="example-box">{{ r.example }}</div>
            </div>

            <div class="rc-foot">
              <span class="dim-chip">{{ r.clause }}</span>
              <div class="rc-actions">
                <el-button link type="primary" @click="locate(r)">
                  <el-icon><Aim /></el-icon> 定位原文
                </el-button>
                <el-button link @click="ignore(r)">忽略本条</el-button>
              </div>
            </div>
          </div>
        </section>
        <el-empty v-if="!groups.length" description="当前筛选下没有匹配的风险点" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import AppTopbar from '../../components/AppTopbar.vue'
import RiskTag from '../../components/RiskTag.vue'
import { getAuditResult } from '../../services/contract.service'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const data = ref(null)
const activeDim = ref('全部')
const levelFilter = ref('all')
const ignored = ref(new Set())

onMounted(load)
async function load() {
  loading.value = true
  try {
    data.value = await getAuditResult(route.params.id)
    activeDim.value = '全部'
  } finally {
    loading.value = false
  }
}

const allRisks = computed(() => (data.value?.risks || []).filter((r) => !ignored.value.has(r)))
const dimTabs = computed(() => ['全部', ...(data.value?.dimensions || [])])
const total = computed(() => allRisks.value.length)
const majorCount = computed(() => allRisks.value.filter((r) => r.level === 'major').length)
const generalCount = computed(() => allRisks.value.filter((r) => r.level === 'general').length)

// 先按维度 Tab + 严重度筛选，再按审核维度分组展示
const filtered = computed(() =>
  allRisks.value.filter(
    (r) =>
      (activeDim.value === '全部' || r.dimension === activeDim.value) &&
      (levelFilter.value === 'all' || r.level === levelFilter.value),
  ),
)

const groups = computed(() => {
  const order = data.value?.dimensions || []
  const map = new Map()
  for (const r of filtered.value) {
    if (!map.has(r.dimension)) map.set(r.dimension, [])
    map.get(r.dimension).push(r)
  }
  return order
    .filter((d) => map.has(d))
    .map((d) => ({ dimension: d, risks: map.get(d) }))
})

function locate(r) {
  ElMessage.info(`定位到：${r.clause}`)
}
function ignore(r) {
  ignored.value = new Set([...ignored.value, r])
}
function onExport() {
  const included = total.value
  ElMessage.success(`将导出 ${included} 条审核意见（已排除 ${ignored.value.size} 条忽略项），导出接口待后端就绪后开放`)
}
</script>

<style scoped>
.result {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 20px;
  overflow: hidden;
  min-height: 0;
}
.pane {
  background: #fff;
  border: 0.667px solid var(--line);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.pane-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-bottom: 0.667px solid var(--line);
}
.pane-title {
  font-weight: 700;
  font-size: 16px;
}
.doc-badge {
  font-size: 11px;
  font-weight: 700;
  color: #5369df;
  background: #eef1ff;
  padding: 2px 7px;
  border-radius: 5px;
  letter-spacing: 0.5px;
}
.doc {
  padding: 22px 26px;
  overflow: auto;
  line-height: 1.95;
  color: #2c3850;
}
.doc h2 {
  font-size: 19px;
  text-align: center;
  margin: 4px 0 20px;
}
.doc h3 {
  font-size: 15.5px;
  margin: 22px 0 6px;
}
.doc p {
  margin: 6px 0;
}
.doc .hl {
  background: #fff2cc;
  padding: 7px 10px;
  border-radius: 4px;
}
.review {
  overflow: hidden;
}
.dim-tabs {
  display: flex;
  gap: 22px;
  padding: 0 20px;
  border-bottom: 0.667px solid var(--line);
}
.dim-tab {
  border: 0;
  background: transparent;
  padding: 12px 0;
  font-size: 14px;
  color: var(--muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.dim-tab.on {
  color: var(--blue);
  font-weight: 600;
  border-bottom-color: var(--blue);
}
.level-pills {
  display: flex;
  gap: 10px;
  padding: 14px 20px 6px;
}
.pill {
  border: 0.667px solid var(--line);
  background: #fff;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  color: #4a5670;
  cursor: pointer;
  transition: all 0.15s;
}
.pill.on {
  background: var(--blue);
  border-color: var(--blue);
  color: #fff;
}
.pill.red.on {
  background: var(--red);
  border-color: var(--red);
}
.pill.amber.on {
  background: var(--amber);
  border-color: var(--amber);
}
.cards {
  padding: 8px 20px 18px;
  overflow: auto;
}
.dim-group {
  margin-bottom: 18px;
}
.dim-group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 12px;
}
.dim-group-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  position: relative;
  padding-left: 10px;
}
.dim-group-name::before {
  content: '';
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  width: 3px;
  border-radius: 3px;
  background: var(--blue);
}
.dim-group-count {
  font-size: 12px;
  color: var(--muted);
}
.risk-card {
  border: 0.667px solid var(--line);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.rc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.rc-no {
  color: var(--muted);
  font-size: 13px;
}
.rc-title {
  font-size: 15px;
  flex: 1;
}
.rc-section {
  margin-bottom: 12px;
}
.rc-section label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 5px;
}
.rc-section p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: #4a5670;
}
.rc-section .pre {
  white-space: pre-line;
}
.example-box {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.7;
  color: #586077;
  white-space: pre-line;
}
.rc-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}
.dim-chip {
  font-size: 12px;
  color: var(--blue);
  background: #eef0fe;
  padding: 3px 10px;
  border-radius: 6px;
}
.rc-actions {
  display: flex;
  gap: 8px;
}
.rc-actions :deep(.el-icon) {
  margin-right: 2px;
}
</style>
