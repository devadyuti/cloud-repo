<template>
  <div>
    <h1>Blog Post 1</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>This is blog post 1. Tests nested path resolution under /blog/.</p>
    <NuxtLink to="/blog">← Back to Blog</NuxtLink>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
