<template>
  <div>
    <h1>Contact</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>This is the contact page. Another route to verify direct URL access behavior.</p>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
