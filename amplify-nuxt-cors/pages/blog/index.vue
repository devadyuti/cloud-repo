<template>
  <div>
    <h1>Blog</h1>
    <p class="route-path">Route: {{ route.path }}</p>
    <p>Blog index page. Tests nested route resolution on Amplify.</p>
    <ul>
      <li><NuxtLink to="/blog/post-1">Post 1</NuxtLink></li>
      <li><NuxtLink to="/blog/post-2">Post 2</NuxtLink></li>
    </ul>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
