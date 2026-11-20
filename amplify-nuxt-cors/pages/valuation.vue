<template>
  <div>
    <h1>Valuation</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>This is the valuation page. Direct URL access to this route should work with SSG but fails with the SPA catch-all rewrite.</p>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
