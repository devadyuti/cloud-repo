// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  ssr: true,

  nitro: {
    preset: 'static'
  },

  runtimeConfig: {
    // Server-only (not exposed to client)
    sanityApiUrl: process.env.NUXT_SANITY_API_URL || 'https://your-project-id.apicdn.sanity.io',
    // Client-exposed
    public: {
      sanityApiUrl: process.env.NUXT_PUBLIC_SANITY_API_URL || 'https://your-project-id.apicdn.sanity.io',
      appVersion: '1.0.0',
      buildMode: 'ssg'
    }
  },

  app: {
    head: {
      title: 'Amplify Nuxt CORS Repro',
      meta: [
        { name: 'description', content: 'Reproduction app for Amplify + Nuxt SSG issues' }
      ]
    }
  },

  compatibilityDate: '2025-01-01'
})
