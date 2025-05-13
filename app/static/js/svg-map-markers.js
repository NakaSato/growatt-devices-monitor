/**
 * SVG Map Marker Integration
 * This script adds markers to the Thailand SVG map
 */

document.addEventListener("DOMContentLoaded", function () {
  // Get the SVG map element
  const svgElement = document.getElementById("thailand-svg");
  if (!svgElement) return;

  // Get the markers group in the SVG
  const markersGroup = document.getElementById("map-markers");
  if (!markersGroup) return;

  // Initialize the plants data
  const plantsData = window.plantsData || [];

  // Add SVG markers to the map
  addMarkersSvg(plantsData);

  /**
   * Add markers to the SVG map
   * @param {Array} plants - Array of plant data objects
   */
  function addMarkersSvg(plants) {
    if (!plants || plants.length === 0) return;

    // Clear existing markers
    while (markersGroup.firstChild) {
      markersGroup.removeChild(markersGroup.firstChild);
    }

    // Add markers for each plant
    plants.forEach((plant) => {
      // Convert plant's lat/lng to SVG coordinates
      const svgCoordinates = gpsToSvg(plant.latitude, plant.longitude);

      // Create marker
      const marker = createSvgMarker(
        plant.id,
        svgCoordinates.x,
        svgCoordinates.y,
        getMarkerColor(plant.status),
        plant
      );

      // Add marker to the group
      markersGroup.appendChild(marker);
    });
  }

  /**
   * Create an SVG marker element
   * @param {string} id - Unique identifier for the marker
   * @param {number} x - SVG x coordinate
   * @param {number} y - SVG y coordinate
   * @param {string} color - Marker color based on status
   * @param {Object} plantData - Plant data object
   * @returns {SVGElement} - The created marker element
   */
  function createSvgMarker(id, x, y, color, plantData) {
    const markerGroup = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "g"
    );
    markerGroup.setAttribute("id", `marker-${id}`);
    markerGroup.setAttribute("class", "svg-marker");
    markerGroup.setAttribute("transform", `translate(${x}, ${y})`);
    markerGroup.setAttribute("data-plant-id", id);

    // Store plant data as attributes
    markerGroup.setAttribute("data-plant-name", plantData.name);
    markerGroup.setAttribute("data-plant-status", plantData.status);
    markerGroup.setAttribute("data-plant-capacity", plantData.capacity);
    markerGroup.setAttribute("data-plant-output", plantData.currentOutput);

    // Create the marker pin
    const pin = document.createElementNS("http://www.w3.org/2000/svg", "path");
    pin.setAttribute("d", "M0,-20 C6,-14 6,-8 0,0 C-6,-8 -6,-14 0,-20");
    pin.setAttribute("fill", color);
    pin.setAttribute("stroke", "#ffffff");
    pin.setAttribute("stroke-width", "1.5");
    pin.setAttribute("class", "marker-pin");

    // Add drop shadow effect
    pin.setAttribute("filter", "url(#drop-shadow)");

    // Add to marker group
    markerGroup.appendChild(pin);

    // Add dot in center
    const centerDot = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "circle"
    );
    centerDot.setAttribute("cx", "0");
    centerDot.setAttribute("cy", "-12");
    centerDot.setAttribute("r", "3");
    centerDot.setAttribute("fill", "#ffffff");

    // Add to marker group
    markerGroup.appendChild(centerDot);

    // Add click event
    markerGroup.addEventListener("click", function () {
      showPlantDetails(plantData);
    });

    // Add hover effects
    markerGroup.addEventListener("mouseenter", function () {
      this.setAttribute("transform", `translate(${x}, ${y}) scale(1.2)`);

      // Show tooltip
      showMarkerTooltip(plantData.name, x, y);
    });

    markerGroup.addEventListener("mouseleave", function () {
      this.setAttribute("transform", `translate(${x}, ${y}) scale(1)`);

      // Hide tooltip
      hideMarkerTooltip();
    });

    return markerGroup;
  }

  /**
   * Show plant details in the sidebar
   * @param {Object} plant - Plant data object
   */
  function showPlantDetails(plant) {
    // Dispatch a custom event that other components can listen for
    const event = new CustomEvent("plant-selected", {
      detail: {
        plant: plant,
        isActive: true,
      },
    });

    document.dispatchEvent(event);
  }

  /**
   * Show tooltip when hovering over a marker
   * @param {string} plantName - Name of the plant
   * @param {number} x - SVG x coordinate
   * @param {number} y - SVG y coordinate
   */
  function showMarkerTooltip(plantName, x, y) {
    // Remove existing tooltip if any
    hideMarkerTooltip();

    // Create tooltip group
    const tooltipGroup = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "g"
    );
    tooltipGroup.setAttribute("id", "marker-tooltip");
    tooltipGroup.setAttribute("transform", `translate(${x + 15}, ${y - 30})`);

    // Create tooltip background
    const tooltipBg = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "rect"
    );
    tooltipBg.setAttribute("width", plantName.length * 7 + 20);
    tooltipBg.setAttribute("height", "24");
    tooltipBg.setAttribute("rx", "4");
    tooltipBg.setAttribute("ry", "4");
    tooltipBg.setAttribute("fill", "rgba(0, 0, 0, 0.75)");

    // Create tooltip text
    const tooltipText = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "text"
    );
    tooltipText.setAttribute("x", "10");
    tooltipText.setAttribute("y", "16");
    tooltipText.setAttribute("fill", "#ffffff");
    tooltipText.setAttribute("font-size", "12");
    tooltipText.textContent = plantName;

    // Add elements to tooltip group
    tooltipGroup.appendChild(tooltipBg);
    tooltipGroup.appendChild(tooltipText);

    // Add tooltip to SVG
    svgElement.appendChild(tooltipGroup);
  }

  /**
   * Hide the marker tooltip
   */
  function hideMarkerTooltip() {
    const tooltip = document.getElementById("marker-tooltip");
    if (tooltip) {
      tooltip.remove();
    }
  }

  /**
   * Convert GPS coordinates to SVG coordinates
   * @param {number} lat - Latitude
   * @param {number} lng - Longitude
   * @returns {Object} - Object with x and y properties
   */
  function gpsToSvg(lat, lng) {
    // Define the bounding box of Thailand in lat/lng
    const thailandBounds = {
      north: 20.4178496, // Max latitude
      south: 5.6366753, // Min latitude
      west: 97.3758964, // Min longitude
      east: 105.589038, // Max longitude
    };

    // Get SVG dimensions
    const svgWidth = svgElement.viewBox.baseVal.width;
    const svgHeight = svgElement.viewBox.baseVal.height;

    // Normalize the coordinates to 0-1 range
    const normalizedX =
      (lng - thailandBounds.west) / (thailandBounds.east - thailandBounds.west);
    const normalizedY =
      (thailandBounds.north - lat) /
      (thailandBounds.north - thailandBounds.south);

    // Convert to SVG coordinates
    const x = normalizedX * svgWidth;
    const y = normalizedY * svgHeight;

    return { x, y };
  }

  /**
   * Get color based on plant status
   * @param {string} status - Plant status
   * @returns {string} - Color code
   */
  function getMarkerColor(status) {
    switch (status) {
      case "active":
        return "#10b981"; // green-500
      case "warning":
        return "#f59e0b"; // amber-500
      case "error":
        return "#ef4444"; // red-500
      case "offline":
      default:
        return "#6b7280"; // gray-500
    }
  }

  // Make the addMarkersSvg function globally available
  window.addMarkersSvg = addMarkersSvg;
});
