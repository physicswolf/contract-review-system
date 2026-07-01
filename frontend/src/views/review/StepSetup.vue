<template>
  <section class="setup">
    <!-- 上传成功横幅 -->
    <div class="banner">
      <p class="banner-main"><b>{{ store.fileName }}</b> 已上传成功</p>
      <p class="banner-sub">
        大模型已完成合同审核类型匹配：{{ store.detectedType }}
        <span class="conf">匹配置信度 {{ store.matchConfidence }}%</span>
      </p>
    </div>

    <!-- 立场 / 类型 两栏 -->
    <div class="two-col">
      <div class="col">
        <h3><i>1.</i> 匹配合同审核类型</h3>
        <p class="col-sub">大模型根据合同内容自动识别，用户可根据实际业务手动调整。</p>
        <div class="field-label-row">
          <label class="field-label">合同类型</label>
          <span class="ai-badge">AI识别</span>
        </div>
        <el-select v-model="auditType" class="full" placeholder="请选择合同类型">
          <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
        </el-select>
        <div class="note">
          合同类型只用于识别、归档和检索；审核规则由本次所选审核点独立决定，两者不做强绑定。
        </div>
      </div>

      <div class="col">
        <h3><i>2.</i> 选择您的审核立场 <span class="req">*</span></h3>
        <p class="col-sub">AI 将基于所选立场进行倾向分析和修改建议。</p>
        <div class="role-grid">
          <button
            v-for="r in roleOptions"
            :key="r.value"
            class="role-card"
            :class="{ on: store.role === r.value }"
            @click="store.role = r.value"
          >
            <b>{{ r.title }}</b>
            <small>{{ r.sub }}</small>
          </button>
        </div>
      </div>
    </div>

    <!-- 审核点 -->
    <div class="points-block">
      <div class="points-head">
        <div>
          <h3>审核点及核心目的</h3>
          <p class="col-sub">默认勾选系统推荐项，可从全部已配置审查风险点中自由增减。</p>
        </div>
        <span class="count-badge">已选 {{ store.selectedPoints.length }} / 共 {{ points.length }} 项</span>
      </div>

      <div class="points-scroll" v-loading="loading">
        <div class="points-grid">
          <div
            v-for="p in points"
            :key="p.id"
            class="pt-card"
            :class="{ on: store.selectedPoints.includes(p.id) }"
            @click="toggle(p.id)"
          >
            <span class="check"><el-icon v-if="store.selectedPoints.includes(p.id)"><Check /></el-icon></span>
            <div class="pt-text">
              <b>{{ p.name }}</b>
              <small>{{ p.category }}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="points-foot">
        <el-button @click="toggleAll">{{ allChecked ? '取消全选' : '全部选择' }}</el-button>
        <span class="foot-hint">展示全部已配置审查风险点，选择区域可独立滚动</span>
      </div>
    </div>

    <!-- 底部操作 -->
    <div class="actions">
      <el-button @click="$emit('back')">重新上传</el-button>
      <el-button type="primary" :loading="submitting" @click="onStart">开始分析</el-button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { reviewStore } from '../../stores/review'
import { listPoints } from '../../services/point.service'

const emit = defineEmits(['back', 'start'])
const store = reviewStore
const loading = ref(false)
const submitting = ref(false)
const points = ref([])
const auditType = ref(store.detectedType || '采购合同')
const typeOptions = ['采购合同', '服务合同', '销售合同', '租赁合同', '合作协议', '其他合同']
const roleOptions = [
  { value: '甲方', title: '甲方立场', sub: '重点保护采购方、委托方权益' },
  { value: '乙方', title: '乙方立场', sub: '重点保护供应方、承接方权益' },
]

onMounted(async () => {
  loading.value = true
  try {
    const { items } = await listPoints()
    points.value = items.filter((p) => p.status === '已启用')
    if (!store.selectedPoints.length) {
      store.selectedPoints = points.value.filter((p) => p.defaultChecked).map((p) => p.id)
    }
  } finally {
    loading.value = false
  }
})

const allChecked = computed(
  () => points.value.length > 0 && store.selectedPoints.length === points.value.length,
)

function toggle(id) {
  const i = store.selectedPoints.indexOf(id)
  if (i > -1) store.selectedPoints.splice(i, 1)
  else store.selectedPoints.push(id)
}
function toggleAll() {
  store.selectedPoints = allChecked.value ? [] : points.value.map((p) => p.id)
}

async function onStart() {
  if (!store.selectedPoints.length) {
    ElMessage.warning('请至少选择一个审核点')
    return
  }
  submitting.value = true
  try {
    await emit('start', auditType.value)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.setup {
  padding-top: 4px;
}
.banner {
  background: #f7f9fd;
  border: 0.667px solid var(--line);
  border-radius: 12px;
  padding: 18px;
  text-align: center;
  margin-bottom: 20px;
}
.banner-main {
  margin: 0 0 6px;
  font-size: 16px;
  color: var(--ink);
}
.banner-sub {
  margin: 0;
  font-size: 14px;
  color: var(--muted);
}
.conf {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--blue);
  background: #eef0fe;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}
.col {
  background: #fff;
}
.col h3 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}
.col h3 i {
  font-style: normal;
  color: var(--blue);
  margin-right: 4px;
}
.col h3 .req {
  color: var(--red);
  margin-left: 2px;
}
.role-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.role-card {
  text-align: left;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s;
}
.role-card:hover {
  border-color: #b9c5e8;
}
.role-card.on {
  border-color: var(--blue);
  background: #f3f5ff;
}
.role-card b {
  display: block;
  font-size: 15px;
  color: var(--ink);
  margin-bottom: 4px;
}
.role-card small {
  font-size: 12.5px;
  color: var(--muted);
}
.col-sub {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--muted);
}
.field-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}
.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.field-label-row .field-label {
  margin: 0;
}
.ai-badge {
  font-size: 12px;
  color: var(--blue);
  background: #eef0fe;
  padding: 2px 8px;
  border-radius: 6px;
}
.full {
  width: 100%;
}
.note {
  margin-top: 12px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.7;
  color: #4a5670;
  background: #eefaf4;
  border-left: 3px solid var(--green);
  border-radius: 8px;
}
.points-block {
  background: #fff;
}
.points-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.points-head h3 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
}
.count-badge {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--blue);
  background: #eef0fe;
  padding: 4px 12px;
  border-radius: 8px;
}
.points-scroll {
  max-height: 320px;
  overflow: auto;
  padding-right: 4px;
}
.points-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.pt-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 0.667px solid var(--line);
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
}
.pt-card:hover {
  border-color: #b9c5e8;
}
.pt-card.on {
  background: #f3f5ff;
  border-color: var(--blue);
}
.check {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 5px;
  border: 1.5px solid #c4cee0;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 13px;
}
.pt-card.on .check {
  background: var(--blue);
  border-color: var(--blue);
}
.pt-text b {
  display: block;
  font-size: 14.5px;
  color: var(--ink);
  font-weight: 600;
}
.pt-text small {
  color: var(--muted);
  font-size: 12.5px;
}
.points-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
}
.foot-hint {
  font-size: 12.5px;
  color: var(--muted);
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px 0 30px;
}
</style>
