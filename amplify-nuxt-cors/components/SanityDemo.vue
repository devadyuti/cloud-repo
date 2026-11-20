<template>
  <div class="sanity-demo">
    <h3>Sanity API — {{ mode === 'direct' ? 'Direct (CORS)' : 'Proxy' }}</h3>

    <div v-if="loading" class="status loading">Loading…</div>

    <div v-else-if="error" class="status error">
      <p><strong>Error Type:</strong> {{ error.type }}</p>
      <p v-if="error.status"><strong>Status:</strong> {{ error.status }}</p>
      <p><strong>URL:</strong> {{ error.url }}</p>
      <p><strong>Message:</strong> {{ error.message }}</p>
    </div>

    <div v-else class="status success">
      <p><strong>Response:</strong></p>
      <pre>{{ JSON.stringify(result, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  mode: {
    type: String,
    required: true,
    validator: (v) => ['direct', 'proxy'].includes(v)
  }
})

const result = ref(null)
const error = ref(null)
const loading = ref(true)

const { fetchDirect, fetchProxy } = useSanity()

if (props.mode === 'proxy') {
  // Proxy mode: fetch at build time via useAsyncData (runs server-side during nuxt generate)
  const config = useRuntimeConfig()
  const query = '*[_type == "page"][0..2]'
  const sanityUrl = `${config.sanityApiUrl || config.public.sanityApiUrl}?query=${encodeURIComponent(query)}`

  const { data: proxyData, error: proxyError } = await useAsyncData(
    'sanity-proxy',
    () => $fetch(sanityUrl).catch((err) => {
      throw createError({ statusCode: 502, message: err.message || 'Upstream API error' })
    })
  )

  if (proxyError.value) {
    error.value = { type: 'http', status: 502, url: sanityUrl, message: proxyError.value.message || 'Build-time fetch failed' }
  } else {
    result.value = proxyData.value
  }
  loading.value = false
} else {
  // Direct mode: fetch client-side (will trigger CORS error)
  onMounted(async () => {
    const query = '*[_type == "page"][0..2]'
    const res = await fetchDirect(query)
    result.value = res.data
    error.value = res.error
    loading.value = false
  })
}
</script>

<style scoped>
.sanity-demo {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
}

.status.loading { color: #666; }
.status.error { color: #c0392b; }
.status.success { color: #27ae60; }

pre {
  background: #f5f5f5;
  padding: 0.5rem;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.85rem;
}
</style>
