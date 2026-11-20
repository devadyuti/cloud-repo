export function useSanity() {
  const config = useRuntimeConfig()

  function classifyError(err, url) {
    if (err.name === 'AbortError') {
      return { type: 'timeout', status: null, url, message: 'Request timed out after 5s' }
    }
    if (err instanceof TypeError) {
      return { type: 'cors', status: null, url, message: 'CORS policy blocked the request' }
    }
    return { type: 'network', status: null, url, message: err.message || 'Network error — endpoint unreachable' }
  }

  async function fetchDirect(query) {
    const url = `${config.public.sanityApiUrl}?query=${encodeURIComponent(query)}`
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)

    try {
      const response = await fetch(url, { signal: controller.signal })
      clearTimeout(timeout)

      if (!response.ok) {
        return {
          data: null,
          error: { type: 'http', status: response.status, url, message: `HTTP ${response.status} error from Sanity API` }
        }
      }

      const data = await response.json()
      return { data, error: null }
    } catch (err) {
      clearTimeout(timeout)
      return { data: null, error: classifyError(err, url) }
    }
  }

  async function fetchProxy(query) {
    const url = `/api/sanity?query=${encodeURIComponent(query)}`
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)

    try {
      const response = await fetch(url, { signal: controller.signal })
      clearTimeout(timeout)

      if (!response.ok) {
        return {
          data: null,
          error: { type: 'http', status: response.status, url, message: `HTTP ${response.status} error from proxy` }
        }
      }

      const data = await response.json()
      return { data, error: null }
    } catch (err) {
      clearTimeout(timeout)
      return { data: null, error: classifyError(err, url) }
    }
  }

  return { fetchDirect, fetchProxy }
}
