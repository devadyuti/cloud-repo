<template>
  <nav class="navbar">
    <NuxtLink
      v-for="link in links"
      :key="link.path"
      :to="link.path"
      class="nav-link"
      :class="{ active: isActive(link.path) }"
    >
      {{ link.label }}
    </NuxtLink>
  </nav>
</template>

<script setup>
const route = useRoute()

const links = [
  { path: '/', label: 'Home' },
  { path: '/valuation', label: 'Valuation' },
  { path: '/login', label: 'Login' },
  { path: '/about', label: 'About' },
  { path: '/contact', label: 'Contact' },
  { path: '/blog', label: 'Blog' },
  { path: '/diagnostics', label: 'Diagnostics' }
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.navbar {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
  flex-wrap: wrap;
}

.nav-link {
  text-decoration: none;
  color: #333;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.nav-link.active {
  background: #333;
  color: #fff;
}
</style>
