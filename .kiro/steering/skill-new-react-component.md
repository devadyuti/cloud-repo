---
inclusion: auto
description: "Use when creating a new React component, building a new UI feature, or adding a page section to the dashboard"
---

# Skill: Create New React Component

## Workflow

When building a new UI component for the portfolio risk dashboard (or any React project in this workspace):

### Step 1: Create the Component File

Create in `frontend/src/components/ComponentName.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Spinner from '@cloudscape-design/components/spinner';
import Alert from '@cloudscape-design/components/alert';

const ComponentName = ({ clientId, onAction }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // API call here
        setData(result);
      } catch (err) {
        setError('Failed to load data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [clientId]);

  if (loading) return <Spinner size="large" />;
  if (error) return <Alert type="error">{error}</Alert>;

  return (
    <Container header={<Header variant="h2">Component Title</Header>}>
      <SpaceBetween size="m">
        {/* Component content */}
      </SpaceBetween>
    </Container>
  );
};

export default ComponentName;
```

### Step 2: Add to Parent Component

Import and render in `App.jsx` or the relevant parent:

```jsx
import ComponentName from './components/ComponentName';

// In the render:
<ComponentName clientId={selectedClient} onAction={handleAction} />
```

### Step 3: Add API Function (if needed)

Create or update `frontend/src/api/`:

```javascript
import { get } from 'aws-amplify/api';

export const fetchComponentData = async (id) => {
  const response = await get({ apiName: 'portfolioApi', path: `/endpoint/${id}` });
  return response.body.json();
};
```

### Step 4: Add Styles (if needed)

Add CSS to `frontend/src/index.css` or create a component-specific CSS file. Prefer Cloudscape tokens over custom colours.

## Cloudscape Components Quick Reference

| Need | Component |
|------|-----------|
| Data table | `Table` |
| Card layout | `Cards` |
| Form inputs | `FormField`, `Input`, `Select` |
| Charts | `PieChart`, `BarChart` (or Recharts for complex) |
| Notifications | `Flashbar`, `Alert` |
| Loading | `Spinner`, `StatusIndicator` |
| Layout | `Container`, `Grid`, `ColumnLayout`, `SpaceBetween` |
| Navigation | `SideNavigation`, `Tabs`, `BreadcrumbGroup` |

## Branding Tokens

```css
:root {
  --color-primary: #1B365D;    /* Navy Blue — headers, nav */
  --color-accent: #B8860B;     /* Gold — buttons, highlights */
  --color-background: #F5F5F5; /* Light Grey — page bg */
}
```

## Checklist

- [ ] Component uses Cloudscape primitives where possible
- [ ] Loading state handled (Spinner)
- [ ] Error state handled (Alert)
- [ ] Props destructured in function signature
- [ ] Default export at bottom of file
- [ ] No inline styles — use CSS classes or Cloudscape tokens
- [ ] Accessible: interactive elements have labels
