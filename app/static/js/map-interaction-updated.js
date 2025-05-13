/**
 * Map Interaction Handler for Satellite View Only
 * Modified to work exclusively with the Leaflet satellite map
 */
document.addEventListener("DOMContentLoaded", function () {
  // Setup tab switching
  setupMapTabs();

  // Setup map type buttons
  setupMapTypeButtons();

  // Additional UI interactions
  setupUIInteractions();
});

/**
 * Set up map tab switching functionality
 */
function setupMapTabs() {
  const satelliteTab = document.getElementById("satellite-tab");
  const leafletMapContainer = document.getElementById("leaflet-map-container");

  // Since we're only showing the satellite map, make sure it's active
  if (satelliteTab && leafletMapContainer) {
    // Ensure Leaflet map is visible
    leafletMapContainer.classList.remove("hidden");
    satelliteTab.classList.add("bg-blue-600", "text-white");
    satelliteTab.classList.remove("bg-white", "text-gray-700");

    // Force refresh the Leaflet map to ensure proper rendering
    if (window.leafletMap) {
      window.leafletMap.invalidateSize();
    }
  }
}

/**
 * Set up map type buttons
 */
function setupMapTypeButtons() {
  const worldMapBtn = document.getElementById("world-map-btn");

  if (worldMapBtn) {
    // Ensure the world map button is active
    worldMapBtn.classList.add("bg-blue-600", "text-white");
    worldMapBtn.classList.remove("bg-gray-100", "text-gray-800");
  }
}

/**
 * Set up additional UI interactions
 */
function setupUIInteractions() {
  // Filter button toggle
  const filterBtn = document.getElementById("filter-btn");
  const filterPanel = document.getElementById("filter-panel");

  if (filterBtn && filterPanel) {
    filterBtn.addEventListener("click", function () {
      filterPanel.classList.toggle("hidden");

      // Update button styling when active
      if (!filterPanel.classList.contains("hidden")) {
        filterBtn.classList.add("bg-blue-100");
      } else {
        filterBtn.classList.remove("bg-blue-100");
      }
    });
  }

  // Export options dropdown
  const exportBtn = document.getElementById("export-btn");
  const exportOptions = document.getElementById("export-options");

  if (exportBtn && exportOptions) {
    exportBtn.addEventListener("click", function () {
      exportOptions.classList.toggle("hidden");
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", function (e) {
      if (!exportBtn.contains(e.target) && !exportOptions.contains(e.target)) {
        exportOptions.classList.add("hidden");
      }
    });
  }

  // Handle apply filters button
  const applyFiltersBtn = document.getElementById("apply-filters");
  if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener("click", function () {
      // Apply filters and refresh the map
      filterMapMarkers();

      // Hide the filter panel
      if (filterPanel) {
        filterPanel.classList.add("hidden");
        if (filterBtn) filterBtn.classList.remove("bg-blue-100");
      }
    });
  }

  // Handle reset filters button
  const resetFiltersBtn = document.getElementById("reset-filters");
  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener("click", function () {
      resetFilters();
    });
  }
}

/**
 * Filter map markers based on selected filters
 */
function filterMapMarkers() {
  // Get filter values
  const statusFilters = getSelectedStatusFilters();
  const capacityValue = document.getElementById("capacity-range")?.value || 0;
  const regionValue = document.getElementById("region-select")?.value || "";
  const searchText = document.getElementById("plant-search")?.value || "";

  // Apply filters to Leaflet markers if available
  if (window.leafletMap && window.leafletMarkers) {
    window.leafletMarkers.forEach((marker) => {
      const plantData = marker.plantData;
      if (!plantData) return;

      // Check if marker matches all filter criteria
      const matchesStatus = statusFilters.includes(plantData.status);
      const matchesCapacity =
        capacityValue === "0" || plantData.capacity <= parseInt(capacityValue);
      const matchesRegion =
        regionValue === "" || plantData.region === regionValue;
      const matchesSearch =
        searchText === "" ||
        plantData.name.toLowerCase().includes(searchText.toLowerCase()) ||
        plantData.id.toLowerCase().includes(searchText.toLowerCase());

      // Show/hide marker based on filter match
      if (matchesStatus && matchesCapacity && matchesRegion && matchesSearch) {
        marker.addTo(window.leafletMap);
      } else {
        marker.removeFrom(window.leafletMap);
      }
    });
  }

  // Show notification
  if (typeof window.showNotification === "function") {
    window.showNotification("Filters applied successfully", "success");
  }
}

/**
 * Get selected status filters
 */
function getSelectedStatusFilters() {
  const statusFilters = [];
  const statusCheckboxes = document.querySelectorAll('input[type="checkbox"]');

  statusCheckboxes.forEach((checkbox) => {
    if (checkbox.checked) {
      const statusLabel = checkbox.nextElementSibling.textContent
        .trim()
        .toLowerCase();
      statusFilters.push(statusLabel);
    }
  });

  return statusFilters.length
    ? statusFilters
    : ["active", "warning", "error", "offline"];
}

/**
 * Reset all filters to default values
 */
function resetFilters() {
  // Reset checkboxes
  document.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    checkbox.checked = true;
  });

  // Reset capacity range
  const capacityRange = document.getElementById("capacity-range");
  const capacityValue = document.getElementById("capacity-value");
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
  const plantSearch = document.getElementById("plant-search");
  if (plantSearch) {
    plantSearch.value = "";
  }

  // Apply reset filters to show all markers
  filterMapMarkers();

  // Show notification
  if (typeof window.showNotification === "function") {
    window.showNotification("Filters reset to defaults", "info");
  }
}
