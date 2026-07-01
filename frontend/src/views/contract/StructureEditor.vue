<template>
  <AppTopbar :title="titleText">
    <template #actions>
      <el-tag :type="dirty ? 'warning' : 'success'" effect="light">{{ dirty ? '未保存' : '已同步' }}</el-tag>
      <el-button @click="backToUpload">
        <el-icon><Back /></el-icon>
        返回上传
      </el-button>
      <el-button :loading="saving" @click="saveOnly">
        <el-icon><FolderChecked /></el-icon>
        保存
      </el-button>
      <el-button type="primary" :loading="saving" @click="finishEditing">
        <el-icon><Check /></el-icon>
        保存并进入审核设置
      </el-button>
    </template>
  </AppTopbar>

  <div class="page" v-loading="loading">
    <div class="doc-head">
      <div>
        <h1>{{ fileName }}</h1>
        <p>{{ schemaName }} · {{ chapterCount }} 个章节 · {{ warningCount }} 个解析告警</p>
      </div>
      <el-tag effect="plain">{{ fileId }}</el-tag>
    </div>

    <el-alert
      v-if="loadError"
      :title="loadError"
      type="error"
      show-icon
      :closable="false"
      class="top-alert"
    />

    <section v-if="structureTree" class="editor-grid">
      <div class="tree-pane">
        <div class="pane-head">
          <div>
            <h2>章节树</h2>
            <span>{{ visibleRoots.length }} 个顶层节点</span>
          </div>
          <el-button size="small" @click="expandTopLevel">
            <el-icon><Expand /></el-icon>
            展开顶层
          </el-button>
        </div>

        <el-scrollbar class="tree-scroll">
          <el-tree
            ref="treeRef"
            :data="visibleRoots"
            node-key="node_id"
            :props="treeProps"
            :expand-on-click-node="false"
            :default-expanded-keys="expandedKeys"
            :current-node-key="selectedNodeId"
            highlight-current
            @node-click="selectNode"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <span class="node-title">
                  <small v-if="data.label">{{ data.label }}</small>
                  {{ data.title || '未命名章节' }}
                </span>
                <el-tag size="small" effect="plain">{{ data.kind || 'unknown' }}</el-tag>
                <span v-if="data.page_no !== null && data.page_no !== undefined" class="page-chip">P{{ data.page_no }}</span>
                <el-tooltip v-if="hasWarnings(data)" content="该节点存在解析告警">
                  <el-icon class="warn"><WarningFilled /></el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-tree>
          <el-empty v-if="!visibleRoots.length" description="暂无章节结构" />
        </el-scrollbar>
      </div>

      <div class="detail-pane">
        <div class="pane-head">
          <div>
            <h2>编辑节点</h2>
            <span>{{ selectedNode ? selectedNode.node_id : '未选择节点' }}</span>
          </div>
          <div class="node-tools">
            <el-button size="small" :disabled="!selectedNode" @click="addChild">
              <el-icon><Plus /></el-icon>
              子节点
            </el-button>
            <el-button size="small" :disabled="!selectedNode" @click="addSibling">
              <el-icon><DocumentAdd /></el-icon>
              兄弟节点
            </el-button>
            <el-button size="small" type="danger" plain :disabled="!selectedNode" @click="deleteSelected">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </div>

        <el-scrollbar class="detail-scroll">
          <el-empty v-if="!selectedNode" description="请在左侧选择一个章节节点" />

          <template v-else>
            <section class="panel-section">
              <h3>基本信息</h3>
              <div class="field-grid">
                <label class="field">
                  <span>编号</span>
                  <el-input v-model="selectedNode.label" @input="markDirty" />
                </label>
                <label class="field wide">
                  <span>标题</span>
                  <el-input v-model="selectedNode.title" type="textarea" :rows="2" @input="markDirty" />
                </label>
                <label class="field">
                  <span>类型</span>
                  <el-input :model-value="selectedNode.kind || 'unknown'" disabled />
                </label>
                <label class="field">
                  <span>页码</span>
                  <el-input :model-value="formatPage(selectedNode.page_no)" disabled />
                </label>
                <label class="field wide">
                  <span>source_ref</span>
                  <el-input :model-value="selectedNode.source_ref || '无'" disabled />
                </label>
              </div>
            </section>

            <section class="panel-section">
              <div class="section-head">
                <h3>正文内容</h3>
                <el-button size="small" @click="addParagraph">
                  <el-icon><Plus /></el-icon>
                  添加段落
                </el-button>
              </div>

              <div v-if="selectedContent.length" class="paragraph-list">
                <div v-for="(item, index) in selectedContent" :key="index" class="paragraph-row">
                  <label class="field">
                    <span>段落 {{ index + 1 }}</span>
                    <el-input
                      v-model="item.text"
                      type="textarea"
                      :rows="4"
                      @input="markDirty"
                    />
                  </label>
                  <el-button type="danger" plain @click="removeParagraph(index)">删除</el-button>
                </div>
              </div>
              <el-empty v-else description="暂无直属正文段落" />
            </section>

            <section class="panel-section">
              <h3>解析告警</h3>
              <div v-if="selectedWarnings.length" class="warning-list">
                <el-alert
                  v-for="(warning, index) in selectedWarnings"
                  :key="index"
                  :title="formatWarning(warning)"
                  type="warning"
                  show-icon
                  :closable="false"
                />
              </div>
              <el-empty v-else description="当前节点无告警" />
            </section>
          </template>
        </el-scrollbar>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Back,
  Check,
  Delete,
  DocumentAdd,
  Expand,
  FolderChecked,
  Plus,
  WarningFilled,
} from '@element-plus/icons-vue'
import AppTopbar from '../../components/AppTopbar.vue'
import { reviewStore } from '../../stores/review'
import {
  getDocument,
  getDocumentStructure,
  saveDocumentStructure,
} from '../../services/document.service'
import { cleanupUpload } from '../../services/contract.service'

const route = useRoute()
const router = useRouter()
const fileId = computed(() => String(route.params.fileId || ''))
const treeRef = ref(null)
const loading = ref(false)
const saving = ref(false)
const dirty = ref(false)
const loadError = ref('')
const documentInfo = ref(null)
const structureTree = ref(null)
const selectedNodeId = ref('')
const expandedKeys = ref([])

const treeProps = { children: 'children', label: 'title' }

const visibleRoots = computed(() => getChildren(structureTree.value))
const selectedNode = computed(() =>
  selectedNodeId.value && structureTree.value ? findNode(structureTree.value, selectedNodeId.value) : null,
)
const selectedContent = computed(() => (selectedNode.value ? ensureContent(selectedNode.value) : []))
const selectedWarnings = computed(() =>
  Array.isArray(selectedNode.value?.warnings) ? selectedNode.value.warnings : [],
)
const fileName = computed(() => documentInfo.value?.origin?.filename || route.query.fileName || fileId.value)
const schemaName = computed(() => documentInfo.value?.schema_name || 'unknown schema')
const chapterCount = computed(() => documentInfo.value?.chapter_count || visibleRoots.value.length)
const warningCount = computed(() => documentInfo.value?.warning_count || countWarnings(structureTree.value))
const titleText = computed(() => `文档结构编辑 · ${fileName.value || '加载中'}`)

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnload)
  load()
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnload)
})

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('当前结构修改尚未保存，确认离开？', '未保存修改', {
      type: 'warning',
      confirmButtonText: '离开',
      cancelButtonText: '继续编辑',
    })
    return true
  } catch {
    return false
  }
})

async function load() {
  if (!fileId.value) {
    loadError.value = '缺少文档 ID，无法加载结构编辑器'
    return
  }

  loading.value = true
  loadError.value = ''
  try {
    const [documentPayload, structurePayload] = await Promise.all([
      getDocument(fileId.value),
      getDocumentStructure(fileId.value),
    ])
    documentInfo.value = documentPayload.document
    structureTree.value = structurePayload.structure
    initializeTreeState()
    dirty.value = false
  } catch (error) {
    loadError.value = error?.response?.data?.detail || error?.message || '结构编辑器加载失败'
  } finally {
    loading.value = false
  }
}

function initializeTreeState() {
  const roots = visibleRoots.value
  expandedKeys.value = roots.map((node) => node.node_id)
  selectedNodeId.value = roots[0]?.node_id || ''
  nextTick(() => {
    if (selectedNodeId.value) treeRef.value?.setCurrentKey(selectedNodeId.value)
  })
}

function selectNode(data) {
  selectedNodeId.value = data.node_id
}

function expandTopLevel() {
  expandedKeys.value = visibleRoots.value.map((node) => node.node_id)
}

function addChild() {
  if (!selectedNode.value) return
  const parent = selectedNode.value
  const node = createEmptyNode(parent.node_id, getNodeDepth(parent.node_id) + 1)
  ensureChildren(parent).push(node)
  expandedKeys.value = [...new Set([...expandedKeys.value, parent.node_id])]
  selectCreatedNode(node)
}

function addSibling() {
  if (!selectedNode.value || !structureTree.value) return
  const parent = findParent(structureTree.value, selectedNode.value.node_id)
  if (!parent) return
  const siblings = ensureChildren(parent)
  const index = siblings.findIndex((node) => node.node_id === selectedNode.value.node_id)
  const node = createEmptyNode(parent.node_id, getNodeDepth(selectedNode.value.node_id))
  siblings.splice(index + 1, 0, node)
  if (parent.node_id !== 'root') expandedKeys.value = [...new Set([...expandedKeys.value, parent.node_id])]
  selectCreatedNode(node)
}

async function deleteSelected() {
  if (!selectedNode.value || selectedNode.value.node_id === 'root' || !structureTree.value) return
  const node = selectedNode.value
  await ElMessageBox.confirm(`确认删除「${node.title || node.label || node.node_id}」及其所有子节点？`, '删除节点', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })

  const parent = findParent(structureTree.value, node.node_id)
  if (!parent || !Array.isArray(parent.children)) return
  parent.children = parent.children.filter((child) => child.node_id !== node.node_id)
  selectedNodeId.value = parent.node_id !== 'root' ? parent.node_id : getChildren(structureTree.value)[0]?.node_id || ''
  markDirty()
}

function addParagraph() {
  if (!selectedNode.value) return
  ensureContent(selectedNode.value).push({ source_ref: '', text: '' })
  markDirty()
}

function removeParagraph(index) {
  if (!selectedNode.value) return
  ensureContent(selectedNode.value).splice(index, 1)
  markDirty()
}

async function saveOnly() {
  if (!structureTree.value) return
  saving.value = true
  try {
    await saveDocumentStructure(fileId.value, structureTree.value)
    dirty.value = false
    ElMessage.success('结构已保存')
  } finally {
    saving.value = false
  }
}

async function finishEditing() {
  if (!canResumeReview()) {
    ElMessage.warning('缺少合同审核上下文，请返回上传页重新上传合同')
    return
  }
  if (dirty.value) await saveOnly()
  syncReviewStoreFromRoute()
  router.push({
    name: 'review',
    query: {
      resume: '1',
      fileId: reviewStore.fileId,
      fileName: reviewStore.fileName,
      detectedType: reviewStore.detectedType,
      matchConfidence: reviewStore.matchConfidence,
    },
  })
}

async function backToUpload() {
  syncReviewStoreFromRoute()
  const fileIdToCleanup = reviewStore.fileId
  const failure = await router.push({ name: 'review' })
  if (failure) return
  if (fileIdToCleanup) {
    try {
      await cleanupUpload(fileIdToCleanup)
    } catch {}
  }
  reviewStore.reset()
}

function syncReviewStoreFromRoute() {
  reviewStore.contractId = String(route.query.contractId || reviewStore.contractId || '')
  reviewStore.fileId = String(route.query.fileId || fileId.value || reviewStore.fileId || '')
  reviewStore.fileName = String(route.query.fileName || fileName.value || reviewStore.fileName || '')
  reviewStore.detectedType = String(route.query.detectedType || reviewStore.detectedType || '未分类')
  reviewStore.matchConfidence = Number(route.query.matchConfidence || reviewStore.matchConfidence || 0)
}

function canResumeReview() {
  return Boolean(route.query.fileId || fileId.value || reviewStore.fileId)
}

function selectCreatedNode(node) {
  selectedNodeId.value = node.node_id
  markDirty()
  nextTick(() => treeRef.value?.setCurrentKey(node.node_id))
}

function markDirty() {
  dirty.value = true
}

function beforeUnload(event) {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

function createEmptyNode(parentId, depth) {
  return {
    node_id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    parent_id: parentId,
    label: '',
    title: '新章节',
    kind: 'custom',
    rank: 50,
    path: [],
    source: 'manual',
    raw_text: '',
    source_ref: '',
    page_no: null,
    line_index: null,
    tree_depth: depth,
    content: [],
    tables: [],
    warnings: [],
    children: [],
  }
}

function findNode(node, nodeId) {
  if (!node) return null
  if (node.node_id === nodeId) return node
  for (const child of getChildren(node)) {
    const found = findNode(child, nodeId)
    if (found) return found
  }
  return null
}

function findParent(node, nodeId) {
  for (const child of getChildren(node)) {
    if (child.node_id === nodeId) return node
    const found = findParent(child, nodeId)
    if (found) return found
  }
  return null
}

function getNodeDepth(nodeId) {
  return findDepth(structureTree.value, nodeId, -1)
}

function findDepth(node, nodeId, depth) {
  if (!node) return 0
  if (node.node_id === nodeId) return depth
  for (const child of getChildren(node)) {
    const found = findDepth(child, nodeId, depth + 1)
    if (found >= 0) return found
  }
  return -1
}

function getChildren(node) {
  return node && Array.isArray(node.children) ? node.children : []
}

function ensureChildren(node) {
  if (!Array.isArray(node.children)) node.children = []
  return node.children
}

function ensureContent(node) {
  if (!Array.isArray(node.content)) node.content = []
  return node.content
}

function hasWarnings(node) {
  return Array.isArray(node.warnings) && node.warnings.length > 0
}

function countWarnings(node) {
  if (!node) return 0
  return (Array.isArray(node.warnings) ? node.warnings.length : 0)
    + getChildren(node).reduce((total, child) => total + countWarnings(child), 0)
}

function formatWarning(warning) {
  if (typeof warning === 'string') return warning
  if (warning && typeof warning === 'object') return warning.message || warning.code || JSON.stringify(warning)
  return String(warning)
}

function formatPage(pageNo) {
  return pageNo === null || pageNo === undefined ? '无' : String(pageNo)
}
</script>

<style scoped>
.page {
  flex: 1;
  min-height: 0;
  padding: 20px 28px 28px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.doc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.doc-head h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.doc-head p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 14px;
}
.top-alert {
  margin-bottom: 14px;
}
.editor-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(320px, 0.9fr) minmax(440px, 1.1fr);
  gap: 16px;
}
.tree-pane,
.detail-pane {
  min-width: 0;
  min-height: 0;
  background: #fff;
  border: 0.667px solid var(--line);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.pane-head {
  min-height: 62px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 0.667px solid var(--line);
}
.pane-head h2 {
  margin: 0;
  font-size: 16px;
}
.pane-head span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}
.tree-scroll,
.detail-scroll {
  flex: 1;
  min-height: 0;
}
.tree-scroll {
  padding: 10px;
}
.tree-node {
  width: 100%;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto;
  align-items: center;
  gap: 8px;
  padding-right: 6px;
}
.node-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 700;
  color: #2c3850;
}
.node-title small {
  margin-right: 6px;
  color: var(--muted);
  font-weight: 700;
}
.page-chip {
  color: var(--muted);
  font-size: 12px;
}
.warn {
  color: var(--amber);
}
.node-tools {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.detail-scroll {
  padding: 20px;
}
.panel-section {
  padding-bottom: 20px;
  margin-bottom: 20px;
  border-bottom: 0.667px solid var(--line);
}
.panel-section:last-child {
  border-bottom: 0;
  margin-bottom: 0;
  padding-bottom: 0;
}
.panel-section h3 {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 700;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.section-head h3 {
  margin: 0;
}
.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field.wide {
  grid-column: 1 / -1;
}
.field span {
  color: #526077;
  font-size: 13px;
  font-weight: 700;
}
.paragraph-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.paragraph-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: end;
}
.warning-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

:deep(.el-tree-node__content) {
  min-height: 38px;
  border-radius: 8px;
}
:deep(.el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content) {
  background: #eef0fe;
}

@media (max-width: 1100px) {
  .page {
    overflow: auto;
  }
  .editor-grid {
    grid-template-columns: 1fr;
    overflow: visible;
  }
  .tree-pane,
  .detail-pane {
    min-height: 420px;
  }
}

@media (max-width: 760px) {
  .doc-head,
  .pane-head,
  .section-head {
    flex-direction: column;
    align-items: stretch;
  }
  .field-grid,
  .paragraph-row {
    grid-template-columns: 1fr;
  }
}
</style>
