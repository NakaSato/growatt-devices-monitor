/**
 * Thailand Solar Plant Map
 * Handles plotting and interaction with solar plant locations on Thailand map
 */

class ThailandSolarMap {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = {
      mapWidth: 800,
      mapHeight: 1000,
      initialZoom: 1,
      maxZoom: 4,
      minZoom: 0.5,
      ...options,
    };

    this.plants = [];
    this.currentZoom = this.options.initialZoom;
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;
    this.viewBox = {
      x: 0,
      y: 0,
      width: this.options.mapWidth,
      height: this.options.mapHeight,
    };
    this.originalViewBox = { ...this.viewBox };

    this.init();
  }

  init() {
    // Set up the SVG container
    this.setupSVGContainer();

    // Add event listeners for pan and zoom
    this.setupEventListeners();
  }

  setupSVGContainer() {
    if (!this.container) {
      console.error("Container element not found");
      return;
    }

    this.svgContainer = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "svg"
    );
    this.svgContainer.setAttribute(
      "viewBox",
      `${this.viewBox.x} ${this.viewBox.y} ${this.viewBox.width} ${this.viewBox.height}`
    );
    this.svgContainer.setAttribute("class", "w-full h-full cursor-grab");
    this.svgContainer.setAttribute("preserveAspectRatio", "xMidYMid meet");
    this.container.appendChild(this.svgContainer);

    // Create a group for the map
    this.mapGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.mapGroup.setAttribute(
      "class",
      "transition-transform duration-300 ease-out"
    );
    this.svgContainer.appendChild(this.mapGroup);

    // Create a group for the plant markers
    this.markerGroup = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "g"
    );
    this.markerGroup.setAttribute("class", "marker-group");
    this.svgContainer.appendChild(this.markerGroup);

    // Add loading indicator
    this.loadingIndicator = document.createElement("div");
    this.loadingIndicator.className =
      "absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white bg-opacity-90 dark:bg-gray-800 dark:bg-opacity-90 px-5 py-3 rounded-lg shadow-md text-sm text-gray-700 dark:text-gray-300";
    this.loadingIndicator.textContent = "Loading map...";
    this.container.appendChild(this.loadingIndicator);
  }

  setupEventListeners() {
    // Zooming with mouse wheel
    this.container.addEventListener("wheel", (e) => {
      e.preventDefault();
      const direction = e.deltaY < 0 ? 1 : -1;
      this.zoom(direction, e.clientX, e.clientY);
    });

    // Pan with mouse drag
    this.svgContainer.addEventListener("mousedown", (e) => {
      this.isDragging = true;
      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;
      this.svgContainer.style.cursor = "grabbing";
    });

    document.addEventListener("mousemove", (e) => {
      if (!this.isDragging) return;

      const dx = e.clientX - this.dragStartX;
      const dy = e.clientY - this.dragStartY;

      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;

      this.pan(dx, dy);
    });

    document.addEventListener("mouseup", () => {
      this.isDragging = false;
      this.svgContainer.style.cursor = "grab";
    });

    // Touch events for mobile devices
    this.svgContainer.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.dragStartX = e.touches[0].clientX;
        this.dragStartY = e.touches[0].clientY;
      }
    });

    document.addEventListener("touchmove", (e) => {
      if (!this.isDragging || e.touches.length !== 1) return;

      const dx = e.touches[0].clientX - this.dragStartX;
      const dy = e.touches[0].clientY - this.dragStartY;

      this.dragStartX = e.touches[0].clientX;
      this.dragStartY = e.touches[0].clientY;

      this.pan(dx, dy);
    });

    document.addEventListener("touchend", () => {
      this.isDragging = false;
    });
  }

  loadMap() {
    fetch("/static/svg/thailand-map.svg")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load Thailand map");
        }
        return response.text();
      })
      .then((svgContent) => {
        // Extract the SVG content and add it to our map group
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(svgContent, "image/svg+xml");
        const svgElement = svgDoc.documentElement;

        // Append all child nodes from the loaded SVG to our map group
        Array.from(svgElement.childNodes).forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            const importedNode = document.importNode(node, true);
            this.mapGroup.appendChild(importedNode);
          }
        });

        // Remove loading indicator
        this.loadingIndicator.remove();
      })
      .catch((error) => {
        console.error("Error loading Thailand map:", error);
        this.loadingIndicator.textContent =
          "Failed to load map. Click to retry.";
        this.loadingIndicator.style.cursor = "pointer";
        this.loadingIndicator.addEventListener("click", () => this.loadMap());
      });
  }

  // Convert GPS coordinates (lat, long) to SVG coordinates
  gpsToSvgCoordinates(lat, lng) {
    // Thailand boundaries (approximated)
    const thaiMinLat = 5.5;
    const thaiMaxLat = 20.5;
    const thaiMinLng = 97.3;
    const thaiMaxLng = 105.7;

    // Map GPS to SVG coordinates (y-axis is inverted)
    const x =
      ((lng - thaiMinLng) / (thaiMaxLng - thaiMinLng)) * this.options.mapWidth;
    const y =
      ((thaiMaxLat - lat) / (thaiMaxLat - thaiMinLat)) * this.options.mapHeight;

    return { x, y };
  }

  // Add a solar plant marker at the specified GPS coordinates
  addPlant(plant) {
    const coords = this.gpsToSvgCoordinates(plant.latitude, plant.longitude);

    // Create marker group
    const markerGroup = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "g"
    );
    markerGroup.setAttribute("class", "plant-marker");
    markerGroup.setAttribute("data-plant-id", plant.id);
    markerGroup.setAttribute(
      "transform",
      `translate(${coords.x}, ${coords.y})`
    );

    // Create marker circle
    const circle = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "circle"
    );
    circle.setAttribute("r", "8");
    circle.setAttribute("fill", this.getStatusColor(plant.status));
    circle.setAttribute("stroke", "#fff");
    circle.setAttribute("stroke-width", "2");

    // Create pulse animation for active plants
    if (plant.status === "active") {
      const pulse = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "circle"
      );
      pulse.setAttribute("r", "8");
      pulse.setAttribute("fill", "rgba(0, 200, 0, 0.3)");
      pulse.setAttribute("class", "pulse-circle");
      markerGroup.appendChild(pulse);
    }

    // Add event listeners
    markerGroup.addEventListener("click", () => this.onPlantClick(plant));
    markerGroup.addEventListener("mouseenter", () =>
      this.showTooltip(plant, coords)
    );
    markerGroup.addEventListener("mouseleave", () => this.hideTooltip());

    // Add elements to the map
    markerGroup.appendChild(circle);
    this.markerGroup.appendChild(markerGroup);

    // Store plant data
    this.plants.push({
      ...plant,
      element: markerGroup,
      coordinates: coords,
    });
  }

  // Add multiple plants at once
  addPlants(plantsData) {
    plantsData.forEach((plant) => this.addPlant(plant));
  }

  // Get color based on plant status
  getStatusColor(status) {
    const colors = {
      active: "#10b981", // Tailwind green-500
      warning: "#f59e0b", // Tailwind amber-500
      error: "#ef4444", // Tailwind red-500
      offline: "#6b7280", // Tailwind gray-500
      maintenance: "#3b82f6", // Tailwind blue-500
    };

    return colors[status] || colors.offline;
  }

  // Show tooltip with plant information
  showTooltip(plant, coords) {
    const tooltip = document.createElement("div");
    tooltip.className =
      "absolute z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 text-sm min-w-[200px] tooltip-animation";
    tooltip.innerHTML = `
      <div class="font-semibold border-b border-gray-200 dark:border-gray-700 pb-1 mb-1">${
        plant.name
      }</div>
      <div class="space-y-1">
        <div>Capacity: ${plant.capacity} kW</div>
        <div>Status: <span class="font-medium ${this.getStatusClass(
          plant.status
        )}">${plant.status}</span></div>
        <div>Current output: ${plant.currentOutput} kW</div>
      </div>
    `;

    // Position the tooltip
    const rect = this.container.getBoundingClientRect();
    const svgPoint = this.svgContainer.createSVGPoint();
    svgPoint.x = coords.x;
    svgPoint.y = coords.y;

    const transformedPoint = svgPoint.matrixTransform(
      this.svgContainer.getScreenCTM()
    );

    tooltip.style.position = "absolute";
    tooltip.style.left = `${transformedPoint.x + rect.left}px`;
    tooltip.style.top = `${transformedPoint.y + rect.top - 120}px`;

    this.container.appendChild(tooltip);
    this.activeTooltip = tooltip;
  }

  // Get Tailwind class for status
  getStatusClass(status) {
    const classes = {
      active: "text-green-600 dark:text-green-400",
      warning: "text-amber-600 dark:text-amber-400",
      error: "text-red-600 dark:text-red-400",
      offline: "text-gray-600 dark:text-gray-400",
      maintenance: "text-blue-600 dark:text-blue-400",
    };

    return classes[status] || classes.offline;
  }

  // Hide tooltip
  hideTooltip() {
    if (this.activeTooltip) {
      this.activeTooltip.remove();
      this.activeTooltip = null;
    }
  }

  // Handle plant click
  onPlantClick(plant) {
    // Dispatch custom event with plant data
    const event = new CustomEvent("plant-selected", { detail: plant });
    document.dispatchEvent(event);

    // Navigate to plant detail page if needed
    if (this.options.navigateOnClick) {
      window.location.href = `/plants/${plant.id}`;
    }
  }

  // Pan the map
  pan(dx, dy) {
    // Convert screen pixels to SVG units
    const svgP = this.screenToSVGPoint(dx, dy);
    const svgZero = this.screenToSVGPoint(0, 0);
    const svgDx = svgZero.x - svgP.x;
    const svgDy = svgZero.y - svgP.y;

    this.viewBox.x += svgDx;
    this.viewBox.y += svgDy;

    this.updateViewBox();
  }

  // Pan to a location with animation
  panToAnimated(x, y, duration = 500) {
    // Calculate the center of the current viewport
    const viewportCenterX = this.viewBox.x + this.viewBox.width / 2;
    const viewportCenterY = this.viewBox.y + this.viewBox.height / 2;

    // Calculate the distance to move
    const dx = x - viewportCenterX;
    const dy = y - viewportCenterY;

    // Use animation frame for smooth transition
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Ease function (ease-out-cubic)
      const easeProgress = 1 - Math.pow(1 - progress, 3);

      // Calculate the new center
      const newX = viewportCenterX + dx * easeProgress;
      const newY = viewportCenterY + dy * easeProgress;

      // Update viewBox
      this.viewBox.x = newX - this.viewBox.width / 2;
      this.viewBox.y = newY - this.viewBox.height / 2;
      this.updateViewBox();

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }

  // Zoom the map
  zoom(direction, clientX, clientY) {
    const zoomFactor = direction > 0 ? 1.2 : 0.8;

    // Ensure zoom is within bounds
    const newZoom = this.currentZoom * zoomFactor;
    if (newZoom < this.options.minZoom || newZoom > this.options.maxZoom)
      return;

    // Convert client coordinates to SVG coordinates
    const svgP = this.screenToSVGPoint(clientX, clientY);

    // Update the viewBox
    const oldWidth = this.viewBox.width;
    const oldHeight = this.viewBox.height;

    this.viewBox.width = this.originalViewBox.width / newZoom;
    this.viewBox.height = this.originalViewBox.height / newZoom;

    // Adjust position to zoom toward cursor
    this.viewBox.x =
      svgP.x -
      ((clientX - this.container.getBoundingClientRect().left) /
        this.container.clientWidth) *
        this.viewBox.width;
    this.viewBox.y =
      svgP.y -
      ((clientY - this.container.getBoundingClientRect().top) /
        this.container.clientHeight) *
        this.viewBox.height;

    this.currentZoom = newZoom;
    this.updateViewBox();
  }

  // Convert screen coordinates to SVG coordinates
  screenToSVGPoint(x, y) {
    const pt = this.svgContainer.createSVGPoint();
    pt.x = x;
    pt.y = y;

    return pt.matrixTransform(this.svgContainer.getScreenCTM().inverse());
  }

  // Update the SVG viewBox
  updateViewBox() {
    this.svgContainer.setAttribute(
      "viewBox",
      `${this.viewBox.x} ${this.viewBox.y} ${this.viewBox.width} ${this.viewBox.height}`
    );
  }

  // Reset the map view to initial state
  resetView() {
    this.viewBox = { ...this.originalViewBox };
    this.currentZoom = this.options.initialZoom;
    this.updateViewBox();
  }

  // Resize handler
  resize() {
    // Maintain aspect ratio and update container
    const containerWidth = this.container.clientWidth;
    const containerHeight = this.container.clientHeight;

    // Adjust viewBox to maintain the map's aspect ratio
    const mapAspectRatio = this.options.mapWidth / this.options.mapHeight;
    const containerAspectRatio = containerWidth / containerHeight;

    if (containerAspectRatio > mapAspectRatio) {
      // Container is wider than the map
      const newWidth = this.viewBox.height * containerAspectRatio;
      this.viewBox.x = this.viewBox.x - (newWidth - this.viewBox.width) / 2;
      this.viewBox.width = newWidth;
    } else {
      // Container is taller than the map
      const newHeight = this.viewBox.width / containerAspectRatio;
      this.viewBox.y = this.viewBox.y - (newHeight - this.viewBox.height) / 2;
      this.viewBox.height = newHeight;
    }

    this.updateViewBox();
  }
}

// Initialize when the DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const mapContainer = document.getElementById("thailand-solar-map");
  if (mapContainer) {
    const solarMap = new ThailandSolarMap("thailand-solar-map", {
      navigateOnClick: true,
      initialZoom: 1.2,
    });

    // Load the map
    solarMap.loadMap();

    // Example: Fetch and add plants from API
    fetch("/api/plants")
      .then((response) => response.json())
      .then((data) => {
        solarMap.addPlants(data.plants);
      })
      .catch((error) => {
        console.error("Error loading plants data:", error);
      });

    // Responsive resize handler
    window.addEventListener("resize", () => {
      solarMap.resize();
    });

    // Make map instance available globally if needed
    window.solarMap = solarMap;

    // Initialize the interaction handler
    if (window.solarMap) {
      const mapInteraction = new MapInteractionHandler(window.solarMap, {
        animationEnabled: true,
        showRegionStats: true,
      });

      // Make the interaction handler available globally if needed
      window.mapInteraction = mapInteraction;
    }
  }
});
