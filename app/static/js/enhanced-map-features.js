/**
 * Enhanced Map Features - Leaflet Satellite Map and Thailand SVG Map
 * Provides interactive map functionality for the Solar Plants Map page
 */

document.addEventListener("DOMContentLoaded", function () {
  // Map tab switching functionality
  const thailandTab = document.getElementById("thailand-tab");
  const satelliteTab = document.getElementById("satellite-tab");
  const thailandMapContainer = document.getElementById(
    "thailand-map-container"
  );
  const leafletMapContainer = document.getElementById("leaflet-map-container");

  // Filter panel controls
  const filterBtn = document.getElementById("filter-btn");
  const filterPanel = document.getElementById("filter-panel");
  const resetFiltersBtn = document.getElementById("reset-filters");
  const applyFiltersBtn = document.getElementById("apply-filters");

  // Map controls
  const zoomInBtn = document.getElementById("zoom-in-btn");
  const zoomOutBtn = document.getElementById("zoom-out-btn");
  const resetViewBtn = document.getElementById("reset-view-btn");
  const fullscreenBtn = document.getElementById("fullscreen-btn");

  // Capacity range slider
  const capacityRange = document.getElementById("capacity-range");
  const capacityValue = document.getElementById("capacity-value");

  // Search input
  const plantSearch = document.getElementById("plant-search");

  // Initialize Leaflet map if container exists
  let leafletMap;
  let markerClusterGroup;

  if (leafletMapContainer) {
    initLeafletMap();
  }

  // Make leafletMap available globally for other modules
  window.leafletMap = leafletMap;

  // Add event listeners for tab switching
  if (thailandTab && satelliteTab) {
    thailandTab.addEventListener("click", () => {
      switchToThailandMap();
    });

    satelliteTab.addEventListener("click", () => {
      switchToSatelliteMap();

      // Check if heatmap controls exist but aren't in the DOM
      const heatmapControls = document.getElementById(
        "heatmap-controls-container"
      );
      const leafletMap = document.getElementById("leaflet-map-container");

      if (
        heatmapControls &&
        leafletMap &&
        !leafletMap.contains(heatmapControls)
      ) {
        leafletMap.appendChild(heatmapControls);
      }
    });
  }

  // Add event listeners for filter panel
  if (filterBtn && filterPanel) {
    filterBtn.addEventListener("click", () => {
      filterPanel.classList.toggle("hidden");
    });
  }

  // Add event listeners for map controls
  if (zoomInBtn && zoomOutBtn && resetViewBtn && fullscreenBtn) {
    zoomInBtn.addEventListener("click", () => {
      if (leafletMap) {
        leafletMap.zoomIn();
      }
    });

    zoomOutBtn.addEventListener("click", () => {
      if (leafletMap) {
        leafletMap.zoomOut();
      }
    });

    resetViewBtn.addEventListener("click", () => {
      if (leafletMap) {
        resetLeafletView();
      }
    });

    fullscreenBtn.addEventListener("click", () => {
      toggleFullscreen(document.querySelector(".lg\\:col-span-3"));
    });
  }

  // Add event listeners for filter controls
  if (capacityRange && capacityValue) {
    capacityRange.addEventListener("input", () => {
      updateCapacityLabel();
    });
  }

  if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener("click", () => {
      applyFilters();
    });
  }

  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener("click", () => {
      resetFilters();
    });
  }

  if (plantSearch) {
    plantSearch.addEventListener("keyup", (e) => {
      if (e.key === "Enter") {
        applyFilters();
      }
    });
  }

  // Map type buttons
  const svgMapBtn = document.getElementById("svg-map-btn");
  const worldMapBtn = document.getElementById("world-map-btn");

  if (svgMapBtn && worldMapBtn) {
    svgMapBtn.addEventListener("click", () => {
      switchToThailandMap();
    });

    worldMapBtn.addEventListener("click", () => {
      switchToSatelliteMap();
    });
  }

  /**
   * Initialize the Leaflet map
   */
  function initLeafletMap() {
    // Create map instance
    leafletMap = L.map("leaflet-map", {
      center: [13.7563, 100.5018], // Bangkok coordinates
      zoom: 6,
      maxZoom: 18,
      minZoom: 5,
      zoomControl: false, // Disable default zoom controls
    });

    // Add tile layer from OpenStreetMap
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(leafletMap);

    // Add satellite layer
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        attribution:
          "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
      }
    ).addTo(leafletMap);

    // Initialize marker cluster group
    markerClusterGroup = L.markerCluster
      .group({
        showCoverageOnHover: false,
        maxClusterRadius: 40,
        iconCreateFunction: function (cluster) {
          const count = cluster.getChildCount();
          const className =
            count < 10
              ? "marker-cluster-small"
              : count < 50
              ? "marker-cluster-medium"
              : "marker-cluster-large";

          return L.divIcon({
            html: `<div><span>${count}</span></div>`,
            className: `marker-cluster ${className}`,
            iconSize: L.point(40, 40),
          });
        },
      })
      .addTo(leafletMap);

    // Add plants to the map
    addPlantsToLeafletMap(window.plantsData || []);

    // Make marker cluster group globally available
    window.markerClusterGroup = markerClusterGroup;
  }

  /**
   * Add plants to the Leaflet map
   */
  function addPlantsToLeafletMap(plants) {
    if (!Array.isArray(plants) || plants.length === 0) return;

    const markers = [];

    plants.forEach((plant) => {
      if (!plant.latitude || !plant.longitude) return;

      // Define marker icon based on plant status
      const markerColor = getMarkerColor(plant.status);
      const markerIcon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="marker-pin bg-${markerColor}-500 animate-pulse-slow"></div>`,
        iconSize: [30, 42],
        iconAnchor: [15, 42],
      });

      // Create marker with popup
      const marker = L.marker([plant.latitude, plant.longitude], {
        icon: markerIcon,
        riseOnHover: true,
        title: plant.name,
      });

      // Attach plant data to marker for filtering
      marker.plantData = plant;

      // Create popup content
      const popupContent = createPopupContent(plant);
      marker.bindPopup(popupContent, {
        maxWidth: 300,
        className: "custom-popup",
      });

      // Add marker to cluster group
      marker.addTo(markerClusterGroup);
      markers.push(marker);
    });

    // Store markers globally for filtering
    window.leafletMarkers = markers;
  }

  /**
   * Create HTML content for marker popup
   */
  function createPopupContent(plant) {
    // Status color class based on plant status
    const statusColor =
      plant.status === "active"
        ? "green"
        : plant.status === "warning"
        ? "yellow"
        : plant.status === "error"
        ? "red"
        : "gray";

    return `
      <div class="plant-popup">
        <div class="flex justify-between mb-2">
          <h3 class="font-bold text-blue-600">${plant.name}</h3>
          <span class="bg-${statusColor}-100 text-${statusColor}-800 text-xs px-2 py-1 rounded-full capitalize">${plant.status}</span>
        </div>
        <div class="text-sm mb-2">
          <p><span class="font-medium">ID:</span> ${plant.id}</p>
          <p><span class="font-medium">Capacity:</span> ${plant.capacity} kW</p>
          <p><span class="font-medium">Today's Energy:</span> ${
            plant.todayEnergy || "0"
          } kWh</p>
          <p><span class="font-medium">Total Energy:</span> ${
            plant.totalEnergy || "0"
          } kWh</p>
        </div>
        <div class="flex justify-end mt-3">
          <a href="/plants/${
            plant.id
          }" class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1 rounded transition-colors">
            View Details
          </a>
        </div>
      </div>
    `;
  }

  /**
   * Switch to satellite map view
   */
  function switchToSatelliteMap() {
    if (!leafletMapContainer || !thailandMapContainer) return;

    // Show Leaflet map and hide Thailand map
    leafletMapContainer.classList.remove("hidden");
    thailandMapContainer.classList.add("hidden");

    // Update tab styling
    if (satelliteTab && thailandTab) {
      satelliteTab.classList.add("bg-blue-600", "text-white");
      satelliteTab.classList.remove(
        "bg-white",
        "text-gray-700",
        "hover:bg-gray-50"
      );
      thailandTab.classList.add(
        "bg-white",
        "text-gray-700",
        "hover:bg-gray-50"
      );
      thailandTab.classList.remove("bg-blue-600", "text-white");
    }

    // Update button styling
    if (worldMapBtn && svgMapBtn) {
      worldMapBtn.classList.add("bg-blue-600", "text-white");
      worldMapBtn.classList.remove("bg-white", "text-gray-800");
      svgMapBtn.classList.add("bg-white", "text-gray-800");
      svgMapBtn.classList.remove("bg-blue-600", "text-white");
    }

    // Refresh Leaflet map to handle container resize
    if (leafletMap) {
      leafletMap.invalidateSize();
    }
  }

  /**
   * Switch to Thailand SVG map view
   */
  function switchToThailandMap() {
    if (!thailandMapContainer || !leafletMapContainer) return;

    // Show Thailand map and hide Leaflet map
    thailandMapContainer.classList.remove("hidden");
    leafletMapContainer.classList.add("hidden");

    // Update tab styling
    if (thailandTab && satelliteTab) {
      thailandTab.classList.add("bg-blue-600", "text-white");
      thailandTab.classList.remove(
        "bg-white",
        "text-gray-700",
        "hover:bg-gray-50"
      );
      satelliteTab.classList.add(
        "bg-white",
        "text-gray-700",
        "hover:bg-gray-50"
      );
      satelliteTab.classList.remove("bg-blue-600", "text-white");
    }

    // Update button styling
    if (svgMapBtn && worldMapBtn) {
      svgMapBtn.classList.add("bg-blue-600", "text-white");
      svgMapBtn.classList.remove("bg-white", "text-gray-800");
      worldMapBtn.classList.add("bg-white", "text-gray-800");
      worldMapBtn.classList.remove("bg-blue-600", "text-white");
    }
  }

  /**
   * Reset Leaflet map view to default
   */
  function resetLeafletView() {
    if (leafletMap) {
      leafletMap.setView([13.7563, 100.5018], 6);
    }
  }

  /**
   * Toggle fullscreen mode for an element
   */
  function toggleFullscreen(element) {
    if (!element) return;

    if (!document.fullscreenElement) {
      if (element.requestFullscreen) {
        element.requestFullscreen();
      } else if (element.webkitRequestFullscreen) {
        element.webkitRequestFullscreen();
      } else if (element.msRequestFullscreen) {
        element.msRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
      }
    }
  }

  /**
   * Update capacity label based on slider value
   */
  function updateCapacityLabel() {
    if (!capacityRange || !capacityValue) return;

    const value = parseInt(capacityRange.value);
    capacityValue.textContent = value === 0 ? "All" : `${value} kW`;
  }

  /**
   * Apply filters to map markers
   */
  function applyFilters() {
    // Get filter values
    const statusFilters = getSelectedStatusFilters();
    const capacityValue = parseInt(capacityRange?.value || 0);
    const regionValue = document.getElementById("region-select")?.value || "";
    const searchText = plantSearch?.value?.toLowerCase() || "";

    // Filter Leaflet markers
    if (window.leafletMarkers) {
      window.leafletMarkers.forEach((marker) => {
        const plant = marker.plantData;
        if (!plant) return;

        // Apply filters
        const matchesStatus = statusFilters.includes(plant.status);
        const matchesCapacity =
          capacityValue === 0 || plant.capacity <= capacityValue;
        const matchesRegion =
          regionValue === "" || plant.region === regionValue;
        const matchesSearch =
          searchText === "" ||
          plant.name.toLowerCase().includes(searchText) ||
          plant.id.toLowerCase().includes(searchText);

        // Show or hide marker
        if (
          matchesStatus &&
          matchesCapacity &&
          matchesRegion &&
          matchesSearch
        ) {
          markerClusterGroup.addLayer(marker);
        } else {
          markerClusterGroup.removeLayer(marker);
        }
      });
    }

    // Hide filter panel
    if (filterPanel) {
      filterPanel.classList.add("hidden");
    }

    // Show notification
    if (typeof window.showNotification === "function") {
      window.showNotification("Filters applied", "success");
    }
  }

  /**
   * Reset all filters to default
   */
  function resetFilters() {
    // Reset status checkboxes
    document.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.checked = true;
    });

    // Reset capacity slider
    if (capacityRange) {
      capacityRange.value = 0;
    }
    if (capacityValue) {
      capacityValue.textContent = "All";
    }

    // Reset region select
    const regionSelect = document.getElementById("region-select");
    if (regionSelect) {
      regionSelect.value = "";
    }

    // Reset search
    if (plantSearch) {
      plantSearch.value = "";
    }

    // Show all markers
    if (window.leafletMarkers && markerClusterGroup) {
      window.leafletMarkers.forEach((marker) => {
        markerClusterGroup.addLayer(marker);
      });
    }

    // Show notification
    if (typeof window.showNotification === "function") {
      window.showNotification("Filters reset", "info");
    }
  }

  /**
   * Get selected status filters
   */
  function getSelectedStatusFilters() {
    const statusFilters = [];
    const statusCheckboxes = document.querySelectorAll(
      'input[type="checkbox"]'
    );

    statusCheckboxes.forEach((checkbox) => {
      if (checkbox.checked && checkbox.nextElementSibling) {
        const statusText = checkbox.nextElementSibling.textContent
          .trim()
          .toLowerCase();
        statusFilters.push(statusText);
      }
    });

    return statusFilters.length > 0
      ? statusFilters
      : ["active", "warning", "error", "offline"];
  }

  /**
   * Get marker color based on plant status
   */
  function getMarkerColor(status) {
    switch (status) {
      case "active":
        return "green";
      case "warning":
        return "yellow";
      case "error":
        return "red";
      default:
        return "gray";
    }
  }
});
