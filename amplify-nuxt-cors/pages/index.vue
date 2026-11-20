<template>
  <div>
    <h1>Home</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>Welcome to the Amplify Nuxt CORS reproduction app. Visit <NuxtLink to="/diagnostics">/diagnostics</NuxtLink> to run automated checks.</p>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
