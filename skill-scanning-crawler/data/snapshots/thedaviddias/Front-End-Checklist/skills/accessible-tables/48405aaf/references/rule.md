# Use semantic table markup for screen readers

> Data tables use proper semantic markup with headers, captions, and scope attributes for screen reader accessibility.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 20 min

---
Proper table markup enables screen readers to announce header-cell relationships, making data understandable.

## Code Example

```html
<table>
  <caption>Q1 2024 Sales by Region</caption>
  <thead>
    <tr>
      <th scope="col">Region</th>
      <th scope="col">January</th>
      <th scope="col">February</th>
      <th scope="col">March</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">North</th>
      <td>$12,000</td>
      <td>$14,500</td>
      <td>$13,200</td>
    </tr>
    <tr>
      <th scope="row">South</th>
      <td>$9,800</td>
      <td>$11,000</td>
      <td>$10,500</td>
    </tr>
  </tbody>
</table>
```

## Why It Matters

Screen readers read table data cell-by-cell—without proper headers, users hear meaningless numbers without context. 'Row 3, Column 2: $99' vs just '$99'.

## Scope Attribute

| Value | Use When |
|-------|----------|
| `scope="col"` | Header applies to column below |
| `scope="row"` | Header applies to row beside it |
| `scope="colgroup"` | Header spans multiple columns |
| `scope="rowgroup"` | Header spans multiple rows |

## Complex Tables with Headers Attribute

```html
<table>
  <caption>Sales Report</caption>
  <thead>
    <tr>
      <th id="region" rowspan="2">Region</th>
      <th id="q1" colspan="2">Q1</th>
      <th id="q2" colspan="2">Q2</th>
    </tr>
    <tr>
      <th id="q1-units" headers="q1">Units</th>
      <th id="q1-revenue" headers="q1">Revenue</th>
      <th id="q2-units" headers="q2">Units</th>
      <th id="q2-revenue" headers="q2">Revenue</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th id="north" headers="region">North</th>
      <td headers="north q1 q1-units">150</td>
      <td headers="north q1 q1-revenue">$15,000</td>
      <td headers="north q2 q2-units">180</td>
      <td headers="north q2 q2-revenue">$18,000</td>
    </tr>
  </tbody>
</table>
```

## React Table Component

```tsx
interface Column{caption}</caption>
      <thead>
        <tr>
          {columns.map(col => (
            <th key={String(col.key)} scope="col">
              {col.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={i}>
            {columns.map(col => {
              const isRowHeader = col.key === rowHeader
              const Tag = isRowHeader ? 'th' : 'td'
              return (
                
                  {String(row[col.key])}
                
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

## Responsive Tables

```html
<!-- Scrollable wrapper for mobile -->
<div class="table-wrapper" tabindex="0" role="region" aria-label="Sales data table">
  <table>
    <!-- Table content -->
  </table>
</div>
```

```css
.table-wrapper {
  overflow-x: auto;
  max-width: 100%;
}

/* Focus indicator for keyboard users scrolling */
.table-wrapper:focus {
  outline: 2px solid #005fcc;
}
```

## Exceptions

- Simple data tables can sometimes fail more from missing header relationships than from missing enhancements such as captions or mobile wrappers, so prioritize the strongest semantic issue.
- Do not convert layout structures into data-table markup just to satisfy a rule; the correct fix may be to remove table semantics entirely.
- When several table-accessibility issues overlap, resolve the header-cell relationship first because downstream announcements depend on it.

## Verification

### Automated Checks

- Use browser accessibility tooling, axe, Lighthouse, or equivalent automated checks against a representative rendered state.

### Manual Checks

- Use screen reader table navigation (Ctrl+Alt+Arrow keys in NVDA)
- Verify headers are announced with each cell
- Check caption describes the table purpose
- Confirm table is not used for layout