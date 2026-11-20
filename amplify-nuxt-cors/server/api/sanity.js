export default defineEventHandler(async (event) => {
  const query = getQuery(event)

  if (!query.query) {
    setResponseStatus(event, 400)
    return { error: true, status: 400, message: 'Missing required "query" parameter' }
  }

  const config = useRuntimeConfig()
  const url = `${config.sanityApiUrl}?query=${encodeURIComponent(query.query)}`

  try {
    const response = await $fetch(url)
    return response
  } catch (err) {
    const status = err?.response?.status || 502
    const message = status === 502 ? 'Upstream API error' : err.message || 'Upstream API error'
    setResponseStatus(event, status)
    return { error: true, status, message }
  }
})
