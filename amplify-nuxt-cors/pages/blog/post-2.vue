<template>
  <div>
    <h1>Blog Post 2</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>This is blog post 2. Another nested route for testing direct URL access.</p>
    <NuxtLink to="/blog">← Back to Blog</NuxtLink>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
