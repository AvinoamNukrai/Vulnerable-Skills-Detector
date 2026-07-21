# Include accessibility testing

> Automate accessibility testing with tools like axe-core, jest-axe, or Playwright's accessibility testing.

**Priority:** high · **Difficulty:** intermediate · **Time:** 30 min

---
Automated accessibility testing catches common WCAG violations before they reach production, protecting your users and reducing legal risk.

## Code Example

```javascript

expect.extend(toHaveNoViolations)

describe('Button', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(
       {}}>Click me
    )
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})

// Test specific rules
it('should have proper color contrast', async () => {
  const { container } = render(Warning)
  const results = await axe(container, {
    rules: {
      'color-contrast': { enabled: true }
    }
  })
  expect(results).toHaveNoViolations()
})
```

## Why It Matters

Automated accessibility testing catches 30-50% of WCAG violations before code reaches users—reducing legal risk and improving usability for everyone.

## Testing Tools

| Tool | Use Case | Framework |
|------|----------|-----------|
| jest-axe | Unit/component tests | Jest |
| @axe-core/playwright | E2E tests | Playwright |
| cypress-axe | E2E tests | Cypress |
| pa11y | CI/CD pipeline | Any |

## Playwright

```typescript

test.describe('Homepage accessibility', () => {
  test('should have no violations', async ({ page }) => {
    await page.goto('/')

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should have no violations on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(results.violations).toEqual([])
  })
})
```

## Cypress

```javascript

describe('Form accessibility', () => {
  beforeEach(() => {
    cy.visit('/contact')
    cy.injectAxe()
  })

  it('should have no violations on load', () => {
    cy.checkA11y()
  })

  it('should have no violations after form errors', () => {
    cy.get('button[type="submit"]').click()
    cy.checkA11y()
  })

  it('should exclude known issues', () => {
    cy.checkA11y(null, {
      rules: {
        'color-contrast': { enabled: false } // Known issue, tracked in backlog
      }
    })
  })
})
```

## CI/CD Integration

```yaml
# GitHub Actions
name: Accessibility Tests
on: [push, pull_request]

jobs:
  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run test:a11y
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: a11y-report
          path: a11y-report.html
```

## Lighthouse CI Accessibility

```json
{
  "ci": {
    "assert": {
      "assertions": {
        "categories:accessibility": ["error", { "minScore": 0.9 }],
        "image-alt": "error",
        "label": "error",
        "link-name": "error"
      }
    }
  }
}
```

## Tools & Validation

Automated checks are a floor, not a ceiling.

Typically caught automatically:

- Missing alt text
- Missing form labels
- Invalid ARIA roles and attributes
- Many color-contrast failures

Usually still manual:

- Whether alt text is actually meaningful
- Keyboard interaction quality in complex widgets
- Screen reader announcements and reading order
- Whether the flow is understandable, not just technically valid

## Verification

### Automated Checks

- Run the accessibility test suite locally and confirm new violations fail the build or test run; the default target should be `<= 0` unexpected axe violations for covered states.
- Pair automated coverage with manual keyboard and screen-reader checks for at least one critical user flow.
- Track ignored or suppressed rules explicitly so temporary exceptions do not become permanent blind spots.

### Manual Checks

- Ensure the suite covers high-risk states such as modal open, form validation errors, and mobile layouts.