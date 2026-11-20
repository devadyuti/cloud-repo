<template>
  <div>
    <h1>Login</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>This is the login page. Tests direct URL access and trailing slash behavior.</p>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
