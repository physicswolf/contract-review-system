<template>
  <span class="risk-tag" :class="normalized">{{ text }}</span>
</template>

<script setup>
import { computed } from 'vue'

// level: red | amber | green ；或传 major/general 自动映射
const props = defineProps({
  level: { type: String, default: 'green' },
  text: { type: String, default: '' },
})

const normalized = computed(() => {
  if (props.level === 'major') return 'red'
  if (props.level === 'general') return 'amber'
  return props.level
})
</script>

<style scoped>
.risk-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 7px;
  font-size: 12.5px;
  font-weight: 600;
}
.risk-tag.red {
  background: #fdeaed;
  color: var(--red);
}
.risk-tag.amber {
  background: #fdf3e2;
  color: var(--amber);
}
.risk-tag.green {
  background: #e7f6ef;
  color: var(--green);
}
.risk-tag.major {
  background: #fdeaed;
  color: var(--red);
}
.risk-tag.general {
  background: #fdf3e2;
  color: var(--amber);
}
</style>
