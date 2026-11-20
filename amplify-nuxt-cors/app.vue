<template>
  <div>
    <NavBar />
    <main class="content">
      <NuxtPage />
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #333;
}

.content {
  padding: 2rem;
  max-width: 960px;
  margin: 0 auto;
}
</style>
