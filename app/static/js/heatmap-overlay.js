/**
 * Heatmap Overlay for Solar Plants Map
 * Provides a visual representation of solar plant density and performance
 */

document.addEventListener("DOMContentLoaded", function () {
  // Check if Leaflet and heatmap libraries are available
  if (!window.L || !L.heatLayer) {
    loadHeatmapLibrary();
  } else {
    initializeHeatmap();
  }

  // Map mode for heatmap (density or performance)
  let heatmapMode = "density"; // Can be 'density' or 'performance'
  let heatmapLayer = null;
  let isHeatmapActive = false;

  /**
   * Load Leaflet.heat library if not already loaded
   */
  function loadHeatmapLibrary() {
    // Create script element for Leaflet.heat
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js";
    script.onload = function () {
      console.log("Leaflet.heat library loaded successfully");
      initializeHeatmap();
    };
    script.onerror = function () {
      console.error("Failed to load Leaflet.heat library");
    };
    document.head.appendChild(script);
  }

  /**
   * Initialize heatmap functionality
   */
  function initializeHeatmap() {
    // Create heatmap toggle button
    createHeatmapControls();

    // Set up event listeners
    setupEventListeners();
  }

  /**
   * Create heatmap controls
   */
  function createHeatmapControls() {
    // Check if map controls container exists
    const mapControlsContainer = document.querySelector(
      ".absolute.bottom-5.right-5"
    );
    if (!mapControlsContainer) return;

    // Create heatmap controls container
    const heatmapControlsContainer = document.createElement("div");
    heatmapControlsContainer.className =
      "absolute bottom-5 left-5 z-10 flex flex-col space-y-2 heatmap-controls-container";
    heatmapControlsContainer.id = "heatmap-controls-container";

    // Create heatmap toggle button
    const heatmapToggleBtn = document.createElement("button");
    heatmapToggleBtn.id = "heatmap-toggle-btn";
    heatmapToggleBtn.className =
      "w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
    heatmapToggleBtn.innerHTML = '<i class="fas fa-fire"></i>';
    heatmapToggleBtn.setAttribute("title", "Toggle heatmap overlay");

    // Create heatmap mode selector
    const heatmapModeSelector = document.createElement("div");
    heatmapModeSelector.id = "heatmap-mode-selector";
    heatmapModeSelector.className =
      "bg-white rounded-lg shadow-md overflow-hidden hidden";
    heatmapModeSelector.innerHTML = `
      <button id="density-mode-btn" class="w-full px-3 py-2 text-sm text-left text-gray-700 hover:bg-gray-50 flex items-center active-mode">
        <i class="fas fa-th mr-2 text-blue-500"></i> Density
      </button>
      <button id="performance-mode-btn" class="w-full px-3 py-2 text-sm text-left text-gray-700 hover:bg-gray-50 flex items-center">
        <i class="fas fa-bolt mr-2 text-yellow-500"></i> Performance
      </button>
    `;

    // Add controls to container
    heatmapControlsContainer.appendChild(heatmapToggleBtn);
    heatmapControlsContainer.appendChild(heatmapModeSelector);

    // Add container to map
    const mapContainer = document.querySelector(".lg\\:col-span-3");
    if (mapContainer) {
      mapContainer.appendChild(heatmapControlsContainer);
    }
  }

  /**
   * Set up event listeners for heatmap controls
   */
  function setupEventListeners() {
    const heatmapToggleBtn = document.getElementById("heatmap-toggle-btn");
    const heatmapModeSelector = document.getElementById(
      "heatmap-mode-selector"
    );
    const densityModeBtn = document.getElementById("density-mode-btn");
    const performanceModeBtn = document.getElementById("performance-mode-btn");

    if (heatmapToggleBtn) {
      heatmapToggleBtn.addEventListener("click", function () {
        toggleHeatmap();
        // Toggle mode selector visibility
        if (heatmapModeSelector) {
          heatmapModeSelector.classList.toggle("hidden");
        }
      });
    }

    if (densityModeBtn) {
      densityModeBtn.addEventListener("click", function () {
        setHeatmapMode("density");
        updateModeButtons(densityModeBtn, performanceModeBtn);
      });
    }

    if (performanceModeBtn) {
      performanceModeBtn.addEventListener("click", function () {
        setHeatmapMode("performance");
        updateModeButtons(performanceModeBtn, densityModeBtn);
      });
    }

    // Close mode selector when clicking elsewhere
    document.addEventListener("click", function (e) {
      if (
        heatmapModeSelector &&
        !heatmapModeSelector.contains(e.target) &&
        e.target !== heatmapToggleBtn
      ) {
        heatmapModeSelector.classList.add("hidden");
      }
    });

    // Listen for map tab changes
    const thailandTab = document.getElementById("thailand-tab");
    const satelliteTab = document.getElementById("satellite-tab");

    if (thailandTab) {
      thailandTab.addEventListener("click", function () {
        if (isHeatmapActive) {
          // Hide heatmap for Thailand SVG map
          toggleHeatmap(false);

          if (heatmapToggleBtn) {
            heatmapToggleBtn.classList.remove("bg-blue-100");
          }
        }
      });
    }

    if (satelliteTab) {
      satelliteTab.addEventListener("click", function () {
        // Restore heatmap state if it was active
        if (isHeatmapActive) {
          setTimeout(() => {
            toggleHeatmap(true);
          }, 500);
        }
      });
    }
  }

  /**
   * Toggle heatmap display
   */
  function toggleHeatmap(forceState) {
    const newState = forceState !== undefined ? forceState : !isHeatmapActive;
    const heatmapToggleBtn = document.getElementById("heatmap-toggle-btn");
    const heatmapLegend = document.getElementById("heatmap-legend");

    // Check if we're on the Leaflet map view
    const leafletContainer = document.getElementById("leaflet-map-container");
    if (leafletContainer && leafletContainer.classList.contains("hidden")) {
      // We're on the Thailand SVG map, don't show heatmap
      showNotification("Heatmap is only available in Satellite view", "info");
      if (heatmapToggleBtn) {
        heatmapToggleBtn.classList.remove("bg-blue-100");
      }
      if (heatmapLegend) {
        heatmapLegend.classList.remove("visible");
      }
      return;
    }

    // Update button state
    if (heatmapToggleBtn) {
      if (newState) {
        heatmapToggleBtn.classList.add("bg-blue-100");
      } else {
        heatmapToggleBtn.classList.remove("bg-blue-100");
      }
    }

    // Toggle heatmap legend
    if (heatmapLegend) {
      if (newState) {
        heatmapLegend.classList.add("visible");
        updateHeatmapLegend();
      } else {
        heatmapLegend.classList.remove("visible");
      }
    }

    // Update state
    isHeatmapActive = newState;

    // Create or remove heatmap layer
    if (isHeatmapActive) {
      createHeatmapLayer();
    } else {
      removeHeatmapLayer();
    }
  }

  /**
   * Create heatmap layer based on current mode
   */
  function createHeatmapLayer() {
    // Check if Leaflet map exists
    if (!window.leafletMap || !L.heatLayer) return;

    // Remove existing layer if any
    removeHeatmapLayer();

    // Get data points based on mode
    const points = getHeatmapData();

    // Create and add heatmap layer
    heatmapLayer = L.heatLayer(points, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      gradient: getGradientByMode(),
    }).addTo(window.leafletMap);

    // Show notification
    const modeText =
      heatmapMode === "density" ? "plant density" : "power output";
    showNotification(`Heatmap showing ${modeText}`, "success");
  }

  /**
   * Remove heatmap layer from map
   */
  function removeHeatmapLayer() {
    if (heatmapLayer && window.leafletMap) {
      window.leafletMap.removeLayer(heatmapLayer);
      heatmapLayer = null;
    }
  }
  /**
   * Set heatmap mode (density or performance)
   */
  function setHeatmapMode(mode) {
    if (mode === heatmapMode) return;

    heatmapMode = mode;

    // Update heatmap legend
    updateHeatmapLegend();

    // Update heatmap if active
    if (isHeatmapActive) {
      createHeatmapLayer();
    }
  }

  /**
   * Update heatmap legend based on current mode
   */
  function updateHeatmapLegend() {
    const legendTitle = document.getElementById("heatmap-legend-title");
    const gradientEl = document.getElementById("heatmap-gradient");

    if (legendTitle && gradientEl) {
      // Update title
      if (heatmapMode === "density") {
        legendTitle.textContent = "Density Heatmap";
        gradientEl.className = "heatmap-gradient density-gradient";
      } else {
        legendTitle.textContent = "Performance Heatmap";
        gradientEl.className = "heatmap-gradient performance-gradient";
      }
    }
  }

  /**
   * Update mode buttons UI
   */
  function updateModeButtons(activeBtn, inactiveBtn) {
    if (activeBtn && inactiveBtn) {
      activeBtn.classList.add("active-mode");
      inactiveBtn.classList.remove("active-mode");
    }

    // Hide mode selector
    const heatmapModeSelector = document.getElementById(
      "heatmap-mode-selector"
    );
    if (heatmapModeSelector) {
      heatmapModeSelector.classList.add("hidden");
    }
  }

  /**
   * Get heatmap data points based on current mode
   */
  function getHeatmapData() {
    // Check if solar plants data exists
    if (!window.solarPlantsData || !window.solarPlantsData.length) {
      return [];
    }

    // Get filtered plants if available
    const plants = window.filteredPlantsData || window.solarPlantsData;

    // Calculate max values for normalization
    const maxCapacity = Math.max(...plants.map((p) => p.capacity || 0));
    const maxOutput = Math.max(...plants.map((p) => p.currentOutput || 0));

    // Create data points
    return plants
      .map((plant) => {
        if (!plant.latitude || !plant.longitude) return null;

        // For density mode, all points have same intensity
        if (heatmapMode === "density") {
          return [plant.latitude, plant.longitude, 0.5];
        }
        // For performance mode, intensity based on current output relative to capacity
        else if (heatmapMode === "performance") {
          const intensity = plant.currentOutput / maxOutput;
          return [plant.latitude, plant.longitude, intensity];
        }
      })
      .filter(Boolean); // Remove any null values
  }

  /**
   * Get color gradient based on mode
   */
  function getGradientByMode() {
    if (heatmapMode === "density") {
      return {
        0.2: "blue",
        0.4: "cyan",
        0.6: "lime",
        0.8: "yellow",
        1.0: "red",
      };
    } else {
      return {
        0.2: "green",
        0.4: "lime",
        0.6: "yellow",
        0.8: "orange",
        1.0: "red",
      };
    }
  }

  /**
   * Helper function to show notification
   */
  function showNotification(message, type = "info") {
    // Try to use existing notification function
    if (typeof window.showNotification === "function") {
      window.showNotification(message, type);
      return;
    }

    // Fallback notification implementation
    let notification = document.getElementById("heatmap-notification");
    if (!notification) {
      notification = document.createElement("div");
      notification.id = "heatmap-notification";
      notification.className =
        "fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 translate-y-20 opacity-0 z-50";
      document.body.appendChild(notification);
    }

    // Set notification type
    notification.className =
      "fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 z-50";

    // Add color based on type
    switch (type) {
      case "success":
        notification.className += " bg-green-500 text-white";
        break;
      case "error":
        notification.className += " bg-red-500 text-white";
        break;
      case "warning":
        notification.className += " bg-yellow-500 text-white";
        break;
      default:
        notification.className += " bg-blue-500 text-white";
    }

    // Set message
    notification.textContent = message;

    // Show notification
    setTimeout(() => {
      notification.classList.remove("translate-y-20", "opacity-0");
    }, 100);

    // Hide notification after 3 seconds
    setTimeout(() => {
      notification.classList.add("translate-y-20", "opacity-0");
    }, 3000);
  }
});
