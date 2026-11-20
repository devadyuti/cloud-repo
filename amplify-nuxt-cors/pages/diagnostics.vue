<template>
  <div>
    <h1>Diagnostics</h1>
    <p>Route: {{ route.path }}</p>

    <section>
      <h2>Sanity.io CMS API Tests</h2>
      <div class="sanity-grid">
        <SanityDemo mode="direct" />
        <SanityDemo mode="proxy" />
      </div>
    </section>

    <section>
      <DiagnosticRunner />
    </section>
  </div>
</template>

<script setup>
const route = useRoute()
</script>

<style scoped>
.sanity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

section {
  margin-bottom: 2rem;
}
</style>
