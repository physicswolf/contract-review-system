<template>
  <header class="topbar">
    <h2 class="topbar-title">{{ title }}</h2>
    <div class="topbar-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup>
defineProps({ title: { type: String, default: '' } })
</script>

<style scoped>
.topbar {
  height: 68px;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 0.667px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
}
.topbar-title {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: var(--ink);
}
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 14px;
}
</style>
