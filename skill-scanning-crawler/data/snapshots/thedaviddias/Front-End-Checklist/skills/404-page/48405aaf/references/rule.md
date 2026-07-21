# Create a custom 404 error page

> A custom 404 error page is designed with helpful navigation options for lost users.

**Priority:** medium · **Difficulty:** beginner · **Time:** 20 min

---
Custom 404 pages transform dead ends into opportunities to guide users back to relevant content.

## Code Example

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Not Found - Site Name</title>
  <meta name="robots" content="noindex">
</head>
<body>
  <main class="error-page">
    <h1>Page Not Found</h1>
    <p>Sorry, the page you're looking for doesn't exist or has been moved.</p>

    <!-- Search -->
    <form action="/search" method="GET" role="search">
      <label for="search">Search our site:</label>
      <input type="search" id="search" name="q" placeholder="What are you looking for?">
      <button type="submit">Search</button>
    </form>

    <!-- Helpful links -->
    <nav aria-label="Helpful links">
      <h2>Try these instead:</h2>
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/products">Products</a></li>
        <li><a href="/blog">Blog</a></li>
        <li><a href="/contact">Contact Us</a></li>
      </ul>
    </nav>
  </main>
</body>
</html>
```

## Why It Matters

A generic browser 404 page causes users to leave immediately—a well-designed custom page provides recovery paths and keeps users engaged with your site.

## Essential Elements

| Element | Purpose |
|---------|---------|
| Clear message | Explain the page wasn't found |
| Search box | Help users find what they need |
| Navigation links | Quick access to main sections |
| Popular content | Suggest relevant pages |
| Home link | Easy return to start |
| Contact option | Report broken links |

## Next.js Implementation

```tsx
// app/not-found.tsx

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h1 className="text-6xl font-bold text-gray-900 mb-4">404</h1>
        <h2 className="text-2xl font-semibold mb-4">Page Not Found</h2>
        <p className="text-gray-600 mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>

        <div className="space-y-4">
          
            Go Home
          

          
            Search Site
          
        </div>

        <nav className="mt-8" aria-label="Popular pages">
          <h3 className="text-sm font-semibold text-gray-500 mb-3">
            Popular Pages
          </h3>
          <ul className="space-y-2">
            <li>Products</li>
            <li>Documentation</li>
            <li>Blog</li>
          </ul>
        </nav>
      </div>
    </main>
  )
}
```

## React Component with Error Tracking

```tsx
interface NotFoundPageProps {
  searchEnabled?: boolean
  popularLinks?: Array<{ href: string; label: string }>
}

  searchEnabled = true,
  popularLinks = []
}: NotFoundPageProps) {
  // Track 404 for analytics
  useEffect(() => {
    // Report to analytics
    if (typeof window !== 'undefined') {
      const path = window.location.pathname
      console.error(`404 Error: ${path}`)

      // Send to analytics service
      analytics?.track('404_error', { path, referrer: document.referrer })
    }
  }, [])

  return (
    <main role="main" className="error-page">
      <div className="error-content">
        <h1>Oops! Page not found</h1>
        <p>
          We couldn't find the page you're looking for.
          It may have been moved or deleted.
        </p>

        {searchEnabled && (
          <form action="/search" method="GET" role="search" className="search-form">
            <label htmlFor="error-search" className="sr-only">
              Search
            </label>
            <input
              type="search"
              id="error-search"
              name="q"
              placeholder="Search..."
              aria-label="Search site"
            />
            <button type="submit">Search</button>
          </form>
        )}

        {popularLinks.length > 0 && (
          <nav aria-label="Suggested pages">
            <h2>You might be looking for:</h2>
            <ul>
              {popularLinks.map(link => (
                <li key={link.href}>
                  <a href={link.href}>{link.label}</a>
                </li>
              ))}
            </ul>
          </nav>
        )}

        <a href="/" className="home-link">
          ← Back to Home
        </a>
      </div>
    </main>
  )
}
```

## Server Configuration

```nginx
# Nginx
server {
    error_page 404 /404.html;
    location = /404.html {
        root /var/www/html;
        internal;
    }
}
```

```apache
# Apache .htaccess
ErrorDocument 404 /404.html
```

## 404 Error Tracking

```tsx
// middleware.ts (Next.js)

  // Log 404s for monitoring
  const response = NextResponse.next()

  // You can check response status and log accordingly
  // This runs before the 404 page renders

  return response
}

// Alternative: Track in the 404 page itself
// app/not-found.tsx
'use client'

  const pathname = usePathname()

  useEffect(() => {
    // Send to error tracking service
    fetch('/api/track-404', {
      method: 'POST',
      body: JSON.stringify({
        path: pathname,
        referrer: document.referrer,
        timestamp: new Date().toISOString()
      })
    })
  }, [pathname])

  return (/* ... */)
}
```

## SEO Considerations

```html
<head>
  <!-- Prevent 404 pages from being indexed -->
  <meta name="robots" content="noindex, nofollow">

  <!-- Return proper 404 status code (server-side) -->
  <!-- Next.js handles this automatically for not-found.tsx -->
</head>
```

## Avoid Soft 404s

A branded "page not found" template is still a search bug if the server responds with `200 OK`. Search engines can treat that as a soft 404, which wastes crawl budget and may surface broken pages in reports.

## Styling Best Practices

```css
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.error-content {
  max-width: 500px;
}

.error-page h1 {
  font-size: 3rem;
  margin-bottom: 1rem;
}

/* Keep consistent with site branding */
.error-page {
  font-family: inherit;
  background: var(--background);
  color: var(--foreground);
}

/* Ensure search is prominent */
.search-form {
  margin: 2rem 0;
}

.search-form input {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  width: 100%;
  max-width: 300px;
}
```

## Verification

1. Navigate to a non-existent URL
2. Verify HTTP 404 status code is returned
3. Check page includes navigation options
4. Test search functionality works
5. Verify page is not indexed (check robots meta)
6. Test on mobile devices
7. Verify screen reader announces content properly
8. Confirm the missing URL appears as a real 404 in DevTools Network, not a 200 soft-404 response

A custom 404 page must return HTTP status code 404, not 200. Search engines treat 200 responses as valid pages, potentially indexing your error page content.