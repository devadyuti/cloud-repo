---
inclusion: fileMatch
fileMatchPattern: "**/*.jsx,**/*.css,**/frontend/**"
---

# Frontend Component Guidelines

## Cloudscape Design System

All UI components should use Cloudscape primitives where possible:
- `Container`, `Header`, `Box`, `SpaceBetween` for layout
- `Table` for data grids (not custom HTML tables)
- `PieChart`, `BarChart` from Cloudscape for simple charts
- `Recharts` for custom/complex visualisations (already in dependencies)
- `Button`, `Link`, `Badge`, `StatusIndicator` for interactive elements
- `Alert` for banners and notifications
- `Cards` for card-based layouts

## Component Pattern

```jsx
import React from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';

const ComponentName = ({ prop1, prop2 }) => {
  return (
    <Container header={<Header variant="h2">Title</Header>}>
      {/* content */}
    </Container>
  );
};

export default ComponentName;
```

## Branding (Client Portfolio Risk Dashboard)

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#1B365D` (Navy Blue) | Header, navigation, primary buttons |
| Secondary | `#B8860B` (Gold) | Accent buttons, insight cards, highlights |
| Background | `#F5F5F5` (Light Grey) | Page background |
| Font | Inter | Body text (Cloudscape default is fine) |

## Rules

- One component per file
- Default export for the component
- Props destructured in function signature
- No inline styles — use CSS classes or Cloudscape tokens
- No emoji in production UI (use StatusIndicator or icons instead)
- Accessibility: all interactive elements need aria labels or visible labels
- Loading states: use Cloudscape `Spinner` or `StatusIndicator` with type "loading"
- Error states: use Cloudscape `Alert` with type "error"

## State Management

- React `useState` and `useEffect` for local state
- No Redux, Zustand, or external state libraries
- API data fetched in the component that needs it (co-located data fetching)
- Pass data down via props — avoid deep prop drilling by keeping component tree shallow
