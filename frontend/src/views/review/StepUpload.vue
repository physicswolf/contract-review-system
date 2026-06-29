<template>
  <section class="card">
    <div
      class="drop"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <div class="drop-icon">⇧</div>
      <h2>拖拽合同到此处上传</h2>
      <p>支持 Word、PDF 格式；拖入并松开即可自动解析</p>
      <div class="drop-actions">
        <button class="btn-pick" @click="pick">选择合同文件</button>
        <button class="btn-demo" @click="useDemo">使用演示合同</button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept=".doc,.docx,.pdf"
        hidden
        @change="onPick"
      />
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['uploaded'])
const fileInput = ref(null)
const dragging = ref(false)

function pick() {
  fileInput.value?.click()
}
function onPick(e) {
  const f = e.target.files?.[0]
  if (f) emit('uploaded', f)
}
function onDrop(e) {
  dragging.value = false
  const f = e.dataTransfer.files?.[0]
  if (f) emit('uploaded', f)
}
function useDemo() {
  emit('uploaded', { name: '智慧园区软件采购合同.docx' })
}
</script>

<style scoped>
.card {
  background: #fff;
  border: 0.667px solid var(--line);
  border-radius: 14px;
  padding: 22.67px;
  box-shadow: 0 10px 15px rgba(38, 56, 88, 0.04);
}
.drop {
  height: 280px;
  border: 2px dashed #b9c5d8;
  border-radius: 15px;
  background: #fafcff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  transition: all 0.15s;
}
.drop.dragging {
  border-color: var(--blue);
  background: #f3f6ff;
}
.drop-icon {
  width: 68px;
  height: 68px;
  margin-bottom: 16px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  font-size: 30px;
  color: #5369df;
  background: #eef1ff;
}
.drop h2 {
  margin: 0 0 5px;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
}
.drop p {
  margin: 0 0 18px;
  font-size: 16px;
  color: var(--muted);
}
.drop-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}
.btn-pick,
.btn-demo {
  height: 40px;
  padding: 0 16px;
  border-radius: 9px;
  font-size: 16px;
  color: #40506a;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-pick {
  border: 0.667px solid #d4dde9;
  font-weight: 600;
}
.btn-demo {
  border: 0.667px solid #d4dde9;
}
.btn-pick:hover,
.btn-demo:hover {
  border-color: var(--blue);
  color: var(--blue);
}
</style>
