<template>
  <AppTopbar title="合同审核" />

  <div class="content">
    <div class="inner">
      <div class="page-head">
        <h1>发起合同审核</h1>
        <p>上传合同后确认审核立场与审核点，合同类型不再限制可选条款。</p>
      </div>

      <!-- 步骤条：标签在上、环形圆圈 -->
      <div class="steps">
        <span class="track"></span>
        <span class="fill" :style="{ width: (step - 1) * 33.333 + '%' }"></span>
        <div v-for="s in stepDefs" :key="s.no" class="step" :class="stepState(s.no)">
          <div class="label">{{ s.label }}</div>
          <div class="circle">
            <el-icon v-if="step > s.no"><Check /></el-icon>
            <span v-else>{{ s.no }}</span>
          </div>
        </div>
      </div>

      <StepUpload v-if="step === 1" @uploaded="onUploaded" />
      <StepSetup v-else-if="step === 2" @back="backToUpload" @start="onStart" />
    </div>
  </div>

  <UploadProgressOverlay ref="overlay" />
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check } from '@element-plus/icons-vue'
import AppTopbar from '../../components/AppTopbar.vue'
import StepUpload from './StepUpload.vue'
import StepSetup from './StepSetup.vue'
import UploadProgressOverlay from '../../components/UploadProgressOverlay.vue'
import { reviewStore } from '../../stores/review'
import { uploadContract, startAudit } from '../../services/contract.service'
import { ENABLE_STRUCTURE_EDITOR } from '../../services/config'

const route = useRoute()
const router = useRouter()
const step = ref(1)
const overlay = ref(null)

const stepDefs = [
  { no: 1, label: '上传合同' },
  { no: 2, label: '确认审核设置' },
  { no: 3, label: '查看审核结果' },
]

function stepState(no) {
  if (step.value > no) return 'done'
  if (step.value === no) return 'active'
  return ''
}

initializeReviewState()

async function onUploaded(file) {
  const [res] = await Promise.all([uploadContract(file), overlay.value.start()])
  reviewStore.contractId = String(res.id || '')
  reviewStore.fileId = String(res.fileId || '')
  reviewStore.fileName = String(res.name || file?.name || '')
  reviewStore.detectedType = String(res.detectedType || '未分类')
  reviewStore.matchConfidence = Number(res.matchConfidence || 0)

  if (res.enableStructureEditor && ENABLE_STRUCTURE_EDITOR && reviewStore.fileId) {
    router.push({
      name: 'structureEditor',
      params: { fileId: reviewStore.fileId },
      query: {
        contractId: reviewStore.contractId,
        fileId: reviewStore.fileId,
        fileName: reviewStore.fileName,
        detectedType: reviewStore.detectedType,
        matchConfidence: reviewStore.matchConfidence,
      },
    })
    return
  }
  step.value = 2
}

async function onStart() {
  await startAudit(reviewStore.contractId, {
    role: reviewStore.role,
    points: reviewStore.selectedPoints,
  })
  step.value = 3
  router.push({ name: 'result', params: { id: reviewStore.contractId } })
}

function initializeReviewState() {
  const shouldResume = route.query.resume === '1' && (queryValue('contractId') || reviewStore.contractId)
  if (!shouldResume) {
    reviewStore.reset()
    return
  }

  restoreReviewContext()
  step.value = 2
}

function restoreReviewContext() {
  reviewStore.contractId = stringQuery('contractId', reviewStore.contractId)
  reviewStore.fileId = stringQuery('fileId', reviewStore.fileId)
  reviewStore.fileName = stringQuery('fileName', reviewStore.fileName)
  reviewStore.detectedType = stringQuery('detectedType', reviewStore.detectedType || '未分类')

  const confidence = Number(stringQuery('matchConfidence', reviewStore.matchConfidence))
  reviewStore.matchConfidence = Number.isFinite(confidence) ? confidence : 0
}

function backToUpload() {
  reviewStore.reset()
  step.value = 1
  if (route.query.resume) router.replace({ name: 'review' })
}

function queryValue(name) {
  const value = route.query[name]
  return Array.isArray(value) ? value[0] : value
}

function stringQuery(name, fallback = '') {
  return String(queryValue(name) || fallback || '')
}
</script>

<style scoped>
.content {
  flex: 1;
  background: #fff;
  display: flex;
  justify-content: center;
  overflow: auto;
}
.inner {
  width: 100%;
  max-width: 1120px;
  padding: 28px;
}
.page-head h1 {
  margin: 0;
  font-size: 25px;
  font-weight: 700;
  color: var(--ink);
}
.page-head p {
  margin: 6px 0 0;
  font-size: 16px;
  color: var(--muted);
}
.steps {
  position: relative;
  display: flex;
  margin: 40px 0 22px;
}
.track,
.fill {
  position: absolute;
  top: 41px;
  height: 3px;
  border-radius: 3px;
}
.track {
  left: 16.666%;
  right: 16.666%;
  background: #e3e8f0;
}
.fill {
  left: 16.666%;
  background: linear-gradient(90deg, #586ff5, #25c9bb);
  transition: width 0.3s;
}
.step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
}
.label {
  height: 24px;
  font-size: 16px;
  color: #9aa5b6;
}
.circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 4px solid #e3e8f0;
  background: #fff;
  display: grid;
  place-items: center;
  font-size: 16px;
  color: #9aa5b6;
}
.step.active .label {
  color: var(--blue);
}
.step.active .circle {
  border-color: var(--blue);
  color: var(--blue);
}
.step.done .label {
  color: var(--blue);
}
.step.done .circle {
  border-color: var(--cyan);
  background: var(--cyan);
  color: #fff;
}
</style>
