export function useDiagnostics() {
  const { routes } = useRouteTests()
  const { fetchDirect } = useSanity()

  const results = ref([])
  const isRunning = ref(false)

  const summary = computed(() => {
    const passed = results.value.filter(r => r.status === 'pass').length
    const failed = results.value.filter(r => r.status === 'fail').length
    const errored = results.value.filter(r => r.status === 'error').length
    return { passed, failed, errored, total: results.value.length }
  })

  async function checkDirectAccess(route) {
    const url = route.path
    try {
      const response = await fetch(url, { redirect: 'follow' })
      const ok = response.ok
      return {
        id: `route-${route.path.replace(/\//g, '-').replace(/^-/, '')}-direct`,
        category: 'route',
        name: `Direct access: ${route.path}`,
        description: `Fetch ${route.path} directly and expect HTTP 200 with correct content`,
        status: ok ? 'pass' : 'fail',
        httpStatus: response.status,
        expected: `HTTP 200 for ${route.path}`,
        actual: `HTTP ${response.status}`,
        url
      }
    } catch (err) {
      return {
        id: `route-${route.path.replace(/\//g, '-').replace(/^-/, '')}-direct`,
        category: 'route',
        name: `Direct access: ${route.path}`,
        description: `Fetch ${route.path} directly and expect HTTP 200 with correct content`,
        status: 'error',
        httpStatus: null,
        expected: `HTTP 200 for ${route.path}`,
        actual: err.message,
        url
      }
    }
  }

  async function checkTrailingSlash(route) {
    // Skip home route — trailing slash is the same URL
    if (route.path === '/') return null

    const url = route.path + '/'
    try {
      const response = await fetch(url, { redirect: 'follow' })
      return {
        id: `trailing-${route.path.replace(/\//g, '-').replace(/^-/, '')}`,
        category: 'trailing-slash',
        name: `Trailing slash: ${url}`,
        description: `Fetch ${url} and expect HTTP 200 with correct content`,
        status: response.ok ? 'pass' : 'fail',
        httpStatus: response.status,
        expected: `HTTP 200 for ${url}`,
        actual: `HTTP ${response.status}`,
        url
      }
    } catch (err) {
      return {
        id: `trailing-${route.path.replace(/\//g, '-').replace(/^-/, '')}`,
        category: 'trailing-slash',
        name: `Trailing slash: ${url}`,
        description: `Fetch ${url} and expect HTTP 200 with correct content`,
        status: 'error',
        httpStatus: null,
        expected: `HTTP 200 for ${url}`,
        actual: err.message,
        url
      }
    }
  }

  async function checkCors() {
    const query = '*[_type == "page"][0]'
    const { error } = await fetchDirect(query)
    const isCors = error && error.type === 'cors'

    return {
      id: 'cors-sanity-direct',
      category: 'cors',
      name: 'CORS: Direct Sanity API call',
      description: 'Client-side fetch to Sanity API should be blocked by CORS',
      status: isCors ? 'pass' : (error ? 'fail' : 'fail'),
      httpStatus: error ? error.status : 200,
      expected: 'CORS error (blocked by browser)',
      actual: error ? `${error.type}: ${error.message}` : 'Request succeeded (no CORS block)',
      url: error ? error.url : 'Sanity API'
    }
  }

  async function checkContent(route) {
    const url = route.path
    try {
      const response = await fetch(url, { redirect: 'follow' })
      if (!response.ok) {
        return {
          id: `content-${route.path.replace(/\//g, '-').replace(/^-/, '')}`,
          category: 'content',
          name: `Content verify: ${route.path}`,
          description: `Verify ${route.path} serves correct page, not home page`,
          status: 'fail',
          httpStatus: response.status,
          expected: `Page title "${route.title}"`,
          actual: `HTTP ${response.status} — could not verify content`,
          url
        }
      }

      const html = await response.text()
      const hasExpectedTitle = html.includes(`<h1>${route.title}</h1>`)
      const hasHomeTitle = route.path !== '/' && html.includes('<h1>Home</h1>')

      let status = 'pass'
      let actual = `Found title "${route.title}"`

      if (!hasExpectedTitle) {
        status = 'fail'
        actual = hasHomeTitle
          ? 'Served home page content instead of correct page (redirect-to-home bug)'
          : `Expected title "${route.title}" not found in response`
      }

      return {
        id: `content-${route.path.replace(/\//g, '-').replace(/^-/, '')}`,
        category: 'content',
        name: `Content verify: ${route.path}`,
        description: `Verify ${route.path} serves correct page, not home page`,
        status,
        httpStatus: response.status,
        expected: `Page title "${route.title}"`,
        actual,
        url
      }
    } catch (err) {
      return {
        id: `content-${route.path.replace(/\//g, '-').replace(/^-/, '')}`,
        category: 'content',
        name: `Content verify: ${route.path}`,
        description: `Verify ${route.path} serves correct page, not home page`,
        status: 'error',
        httpStatus: null,
        expected: `Page title "${route.title}"`,
        actual: err.message,
        url
      }
    }
  }

  async function runAll() {
    isRunning.value = true
    results.value = []

    const allResults = []

    // Direct URL access checks
    for (const route of routes) {
      allResults.push(await checkDirectAccess(route))
    }

    // Trailing slash checks
    for (const route of routes) {
      const result = await checkTrailingSlash(route)
      if (result) allResults.push(result)
    }

    // CORS check
    allResults.push(await checkCors())

    // Content verification checks
    for (const route of routes) {
      allResults.push(await checkContent(route))
    }

    results.value = allResults
    isRunning.value = false
  }

  return { results, summary, runAll, isRunning }
}
