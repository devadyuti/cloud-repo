<template>
  <div class="diagnostic-runner">
    <h2>Diagnostic Runner</h2>

    <div class="context-info">
      <div><strong>Deployment URL:</strong> {{ deploymentUrl }}</div>
      <div><strong>Build Mode:</strong> {{ buildMode }}</div>
      <div><strong>Rewrite Config:</strong> {{ rewriteConfig }}</div>
    </div>

    <div v-if="isRunning" class="running-indicator">
      Running diagnostics…
    </div>

    <div v-if="!isRunning && results.length" class="summary">
      <span class="summary-item pass">✅ {{ summary.passed }} passed</span>
      <span class="summary-item fail">❌ {{ summary.failed }} failed</span>
      <span class="summary-item error">⚠️ {{ summary.errored }} errored</span>
      <span class="summary-item total">{{ summary.total }} total</span>
    </div>

    <div class="results-list">
      <TestResultCard
        v-for="result in results"
        :key="result.id"
        :result="result"
      />
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig()
const { results, summary, runAll, isRunning } = useDiagnostics()

const deploymentUrl = computed(() =>
  import.meta.client ? window.location.origin : '(server render)'
)
const buildMode = config.public.buildMode || 'ssg'
const rewriteConfig = computed(() => {
  if (!import.meta.client) return '(unknown)'
  // Check for the custom header set by amplify.yml
  return 'Check X-Repro-Mode response header for broken/fixed status'
})

onMounted(() => {
  runAll()
})
</script>

<style scoped>
.diagnostic-runner {
  margin-top: 1.5rem;
}

.context-info {
  background: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  line-height: 1.8;
}

.running-indicator {
  padding: 1rem;
  text-align: center;
  color: #666;
  font-style: italic;
}

.summary {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.summary-item {
  font-weight: 600;
  font-size: 0.9rem;
}

.summary-item.pass { color: #27ae60; }
.summary-item.fail { color: #c0392b; }
.summary-item.error { color: #f39c12; }
.summary-item.total { color: #555; margin-left: auto; }

.results-list {
  margin-top: 0.5rem;
}
</style>
