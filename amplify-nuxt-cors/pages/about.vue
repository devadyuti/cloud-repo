<template>
  <div>
    <h1>About</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>This is the about page. When the SPA catch-all rule is active, this page serves home content instead.</p>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
