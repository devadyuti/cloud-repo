export function useRouteTests() {
  const routes = [
    { path: '/', title: 'Home' },
    { path: '/valuation', title: 'Valuation' },
    { path: '/login', title: 'Login' },
    { path: '/about', title: 'About' },
    { path: '/contact', title: 'Contact' },
    { path: '/blog', title: 'Blog' },
    { path: '/blog/post-1', title: 'Blog Post 1' },
    { path: '/blog/post-2', title: 'Blog Post 2' }
  ]

  return { routes }
}
