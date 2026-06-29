<template>
  <transition name="fade">
    <div v-if="visible" class="overlay">
      <div class="overlay-head">合同审核</div>
      <div class="overlay-body">
        <div class="stepper">
          <div class="steps">
            <div class="track" :style="{ width: trackWidth }"></div>
            <div class="step" :class="stepClass(0)">
              <div class="circle">1</div>
              <b>文件上传</b>
              <span>{{ percents[0] }}%</span>
            </div>
            <div class="step" :class="stepClass(1)">
              <div class="circle">2</div>
              <b>文件解析</b>
              <span>{{ percents[1] }}%</span>
            </div>
            <div class="step" :class="stepClass(2)">
              <div class="circle">✓</div>
              <b>解析完成</b>
              <span>{{ stage >= 2 ? '100%' : '等待解析' }}</span>
            </div>
          </div>
          <div class="note">{{ note }}</div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref } from 'vue'

const visible = ref(false)
const stage = ref(0) // 0 上传中 1 解析中 2 完成
const percents = ref([0, 0])
const note = ref('')

const trackWidth = ref('0%')

function stepClass(i) {
  if (stage.value > i) return 'done'
  if (stage.value === i) return 'active'
  return ''
}

function runPercent(idx, duration) {
  return new Promise((resolve) => {
    const tick = 50
    const step = 100 / (duration / tick)
    let v = 0
    const timer = setInterval(() => {
      v = Math.min(100, v + step)
      percents.value[idx] = Math.round(v)
      if (v >= 100) {
        clearInterval(timer)
        resolve()
      }
    }, tick)
  })
}

// 对外暴露：开始进度，结束后 resolve
async function start() {
  visible.value = true
  stage.value = 0
  percents.value = [0, 0]
  trackWidth.value = '0%'
  note.value = '正在安全上传合同文件，请勿关闭页面'

  await runPercent(0, 900)
  stage.value = 1
  trackWidth.value = '50%'
  note.value = '正在识别文档结构、条款和合同主体信息'

  await runPercent(1, 1200)
  stage.value = 2
  trackWidth.value = '100%'
  note.value = '解析完成，正在进入审核设置'

  await new Promise((r) => setTimeout(r, 500))
  visible.value = false
}

defineExpose({ start })
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: #fff;
}
.overlay-head {
  height: 64px;
  padding: 0 30px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--line);
  font-size: 18px;
  font-weight: 800;
}
.overlay-body {
  height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.stepper {
  width: min(760px, 78%);
}
.steps {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  position: relative;
}
.steps:before {
  content: '';
  position: absolute;
  left: 16.7%;
  right: 16.7%;
  top: 28px;
  height: 4px;
  border-radius: 4px;
  background: #e7ebf2;
}
.track {
  position: absolute;
  left: 16.7%;
  top: 28px;
  height: 4px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--blue), var(--cyan));
  transition: width 0.25s;
  max-width: 66.6%;
}
.step {
  position: relative;
  text-align: center;
  z-index: 2;
  color: var(--muted);
}
.circle {
  width: 58px;
  height: 58px;
  margin: 0 auto 13px;
  border: 5px solid #e7ebf2;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #fff;
  font-size: 20px;
  font-weight: 700;
  color: #aab4c5;
}
.step.active .circle {
  border-color: var(--blue);
  color: var(--blue);
}
.step.done .circle {
  border-color: var(--cyan);
  background: var(--cyan);
  color: #fff;
}
.step b {
  display: block;
  color: var(--ink);
}
.step span {
  font-size: 13px;
}
.note {
  text-align: center;
  margin-top: 36px;
  color: var(--muted);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
