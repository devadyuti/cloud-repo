<template>
  <div class="test-result-card" :class="result.status">
    <div class="card-header">
      <span class="status-icon" aria-hidden="true">{{ statusIcon }}</span>
      <span class="test-name">{{ result.name }}</span>
      <span class="category-badge">{{ result.category }}</span>
    </div>

    <div class="card-body">
      <div class="detail-row">
        <span class="label">HTTP Status:</span>
        <span class="value">{{ result.httpStatus ?? '—' }}</span>
      </div>
      <div class="detail-row">
        <span class="label">Expected:</span>
        <span class="value">{{ result.expected }}</span>
      </div>
      <div class="detail-row">
        <span class="label">Actual:</span>
        <span class="value">{{ result.actual }}</span>
      </div>
      <div class="detail-row">
        <span class="label">URL:</span>
        <span class="value url">{{ result.url }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const statusIcon = computed(() => {
  switch (props.result.status) {
    case 'pass': return '✅'
    case 'fail': return '❌'
    default: return '⚠️'
  }
})
</script>

<style scoped>
.test-result-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  border-left: 4px solid #999;
}

.test-result-card.pass { border-left-color: #27ae60; }
.test-result-card.fail { border-left-color: #c0392b; }
.test-result-card.error { border-left-color: #f39c12; }

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.status-icon { font-size: 1.1rem; }

.test-name {
  font-weight: 600;
  flex: 1;
}

.category-badge {
  font-size: 0.75rem;
  background: #eee;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.card-body { padding-left: 1.75rem; }

.detail-row {
  display: flex;
  gap: 0.5rem;
  font-size: 0.875rem;
  line-height: 1.6;
}

.label {
  font-weight: 500;
  min-width: 5.5rem;
  color: #666;
}

.value.url {
  word-break: break-all;
  color: #555;
}
</style>
