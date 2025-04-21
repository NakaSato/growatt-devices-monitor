# Enhanced SVG Maps Guide

This document provides instructions on how to use the enhanced SVG map features in your project.

## Features

- **Responsive Design**: Maps scale automatically to fit container
- **Interactive Elements**: Hover effects and click events
- **Improved Styling**: Better visual appearance with smooth transitions
- **Optimized Performance**: Efficient rendering and interaction
- **Animations and Transitions**: Smooth visual feedback
- **Zoom and Pan**: Interactive navigation of large maps
- **Accessibility**: Keyboard navigation and screen reader support

## Quick Start

1. Include the required files in your HTML:

```html
<link rel="stylesheet" href="/static/css/svg-map-styles.css" />
<script src="/static/js/svg-map-enhancer.js"></script>
```

2. Create a container for your SVG map:

```html
<div class="svg-map-container" id="map-container">
  <!-- Your SVG will go here -->

  <!-- Optional controls -->
  <div class="svg-map-controls">
    <button id="zoom-in" aria-label="Zoom in">+</button>
    <button id="zoom-out" aria-label="Zoom out">-</button>
    <button id="reset-view" aria-label="Reset view">↺</button>
  </div>
</div>
```

3. Initialize the enhancer with your SVG:

```javascript
document.addEventListener("DOMContentLoaded", function () {
  // Option 1: If SVG is already in the DOM
  const svg = document.querySelector("#map-container svg");
  const mapEnhancer = new SVGMapEnhancer(svg);

  // Option 2: Load SVG from a file
  fetch("/path/to/your/map.svg")
    .then((response) => response.text())
    .then((svgContent) => {
      const container = document.getElementById("map-container");
      container.innerHTML = svgContent + container.innerHTML;
      const svg = container.querySelector("svg");
      const mapEnhancer = new SVGMapEnhancer(svg);
    });

  // Connect control buttons
  document.getElementById("zoom-in").addEventListener("click", () => {
    mapEnhancer.zoomIn();
  });

  document.getElementById("zoom-out").addEventListener("click", () => {
    mapEnhancer.zoomOut();
  });

  document.getElementById("reset-view").addEventListener("click", () => {
    mapEnhancer.reset();
  });
});
```

## Preparing Your SVG Maps

To get the most out of the enhancer, prepare your SVG maps as follows:

1. **Add IDs to interactive elements**: Each path, polygon, etc. should have a unique ID
2. **Add data attributes**: Use data attributes to store information about regions
3. **Set titles or aria-labels**: For tooltips and accessibility

Example:

```svg
<path
    id="region-1"
    d="M10,10 L20,20 L30,10 Z"
    data-name="Region 1"
    data-value="42"
    data-info="Additional information"
    aria-label="Region 1 - Click for details"
></path>
```

## Handling Events

The enhancer fires a custom event `svgmapselect` when a user selects an element:

```javascript
svg.addEventListener("svgmapselect", function (event) {
  const detail = event.detail;
  // detail contains:
  // - element: the selected DOM element
  // - id: the element's id
  // - data: dataset object with all data-* attributes

  console.log("Selected:", detail.element.dataset.name);
});
```

## Configuration Options

When creating a new SVGMapEnhancer, you can pass an options object:

```javascript
const mapEnhancer = new SVGMapEnhancer(svg, {
  zoomFactor: 0.1, // How much each zoom step changes
  maxZoom: 5, // Maximum zoom level
  minZoom: 0.5, // Minimum zoom level
  panFactor: 10, // Pan speed with keyboard
  hoverClass: "svg-hover", // CSS class for hover state
  activeClass: "svg-active", // CSS class for selected state
  tooltipClass: "svg-tooltip", // CSS class for tooltips
  enableZoom: true, // Enable zoom functionality
  enablePan: true, // Enable pan functionality
  enableTooltips: true, // Enable tooltips on hover
});
```

## API Methods

The enhancer provides several methods for programmatic control:

- `zoomIn()`: Zoom in one step
- `zoomOut()`: Zoom out one step
- `reset()`: Reset view to original position and scale
- `panTo(x, y)`: Pan to specific coordinates
- `highlightElement(id)`: Highlight a specific element by ID

Example:

```javascript
// Zoom in
mapEnhancer.zoomIn();

// Reset to original view
mapEnhancer.reset();

// Highlight and pan to a specific region
mapEnhancer.highlightElement("region-5");
```

## Accessibility Features

The enhancer makes SVG maps accessible with:

- Keyboard navigation (arrow keys to pan, +/- to zoom)
- ARIA attributes for screen readers
- Focus indicators for interactive elements
- Keyboard selection (Enter or Space to select)

## Mobile Support

The enhancer works on touch devices with:

- Touch panning (drag to pan)
- Pinch-to-zoom (when supported by the browser)
- Responsive layout adjustments

## Performance Tips

For large or complex SVG maps:

1. Simplify paths where possible
2. Group related elements
3. Consider loading detailed regions only when zoomed in
4. Set `enableTooltips: false` if not needed
5. Limit the number of interactive elements

## Browser Compatibility

The enhancer works in all modern browsers:

- Chrome, Firefox, Safari, Edge (latest versions)
- Limited functionality in IE11
