# Template Components

This directory contains reusable components for the Growatt device monitoring application.

## Directory Structure

```
components/
├── alerts/            # Alert and notification components
├── cards/             # Card UI components for displaying data
├── chart/             # Chart and visualization components
├── common/            # Common UI elements used across the application
├── forms/             # Form inputs and controls
├── layouts/           # Layout components (grids, sections, etc.)
├── shared/            # Shared resources (fonts, scripts, styles)
├── svg/               # SVG icons and graphics
└── [feature]/         # Feature-specific components
```

## Usage

Components are organized as Jinja macros that can be imported and used across templates.

### Example Usage

```jinja
{# Import component macros #}
{% from "components/layouts/card.html" import metric_card %}
{% from "components/forms/inputs.html" import text_input, button %}

{# Use in a template #}
<div class="container">
  {% call metric_card(title="Energy Production", value="12.5 kWh", icon="fas fa-bolt", color="green") %}
    <p class="text-sm text-gray-500 mt-2">Daily production is above average</p>
  {% endcall %}
  
  <form action="/submit" method="post">
    {{ text_input(name="username", label="Username", required=true) }}
    {{ button(text="Submit", type="submit", color="blue") }}
  </form>
</div>
```

## Available Components

### Layouts

- **Card Layout** - `layouts/card.html`
  - `standard_card` - Basic card with optional header/footer
  - `metric_card` - Display metrics with title, value, and icon
  - `status_card` - Shows status indicators with appropriate colors

- **Grid Layout** - `layouts/grid.html`
  - `standard_grid` - Responsive grid system with configurable columns
  - `sidebar_layout` - Two-column layout with configurable widths
  - `section` - Section container with title and content

### Forms

- **Form Inputs** - `forms/inputs.html`
  - `text_input` - Standard text input field
  - `select` - Dropdown select component
  - `checkbox` - Checkbox input with label
  - `textarea` - Multi-line text input
  - `button` - Configurable button styles

### Alerts

- **Notifications** - `alerts/notifications.html`
  - `alert` - Contextual alert messages
  - `toast` - Popup notifications that auto-dismiss
  - `notification_badge` - Badge for showing counts

## Best Practices

1. **Composition over Inheritance** - Build complex UIs by composing simple components
2. **Consistent Naming** - Follow naming conventions for classes and variables
3. **Mobile-First Design** - All components are built with responsive design in mind
4. **Configurable Components** - Use parameters to make components flexible
5. **Documentation** - Add comments to explain complex component behavior

## Adding New Components

1. Create a new file in the appropriate directory
2. Define the component using Jinja macros
3. Use consistent parameter ordering and defaults
4. Add documentation comments as needed
5. Update this README with any significant additions 