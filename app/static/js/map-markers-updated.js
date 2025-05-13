/**
 * Map Markers Module - Add custom markers to maps
 * Provides functionality to add, edit, and manage custom markers on both SVG and Leaflet maps
 */

document.addEventListener("DOMContentLoaded", function () {
  // Check if maps are available
  const thailandMapContainer = document.getElementById(
    "thailand-map-container"
  );
  const leafletMapContainer = document.getElementById("leaflet-map-container");

  if (!thailandMapContainer && !leafletMapContainer) return;

  // Initialize marker manager
  const markerManager = new MapMarkerManager();

  // Add marker button to map controls
  addMarkerControls();

  // Add marker list panel
  addMarkerListPanel();

  /**
   * Add marker control buttons to the map
   */
  function addMarkerControls() {
    const mapControlsContainer = document.querySelector(
      ".absolute.bottom-5.right-5"
    );

    if (!mapControlsContainer) return;

    // Create marker button
    const addMarkerButton = document.createElement("button");
    addMarkerButton.id = "add-marker-btn";
    addMarkerButton.className =
      "w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
    addMarkerButton.innerHTML = '<i class="fas fa-map-marker-alt"></i>';
    addMarkerButton.setAttribute("title", "Add marker");

    // Add event listener for marker button
    addMarkerButton.addEventListener("click", function () {
      markerManager.toggleMarkerMode();
    });

    // Add button to controls
    mapControlsContainer.appendChild(addMarkerButton);

    // Create marker list button
    const markerListButton = document.createElement("button");
    markerListButton.id = "marker-list-btn";
    markerListButton.className =
      "w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
    markerListButton.innerHTML = '<i class="fas fa-list"></i>';
    markerListButton.setAttribute("title", "Show marker list");

    // Add event listener for marker list button
    markerListButton.addEventListener("click", function () {
      toggleMarkerListPanel();
    });

    // Add button to controls
    mapControlsContainer.appendChild(markerListButton);
  }

  /**
   * Add marker list panel to the map
   */
  function addMarkerListPanel() {
    // Create panel container
    const panelContainer = document.createElement("div");
    panelContainer.id = "marker-list-panel";
    panelContainer.className =
      "fixed right-5 top-20 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 z-30 w-64 border border-gray-100 dark:border-gray-700 transform transition-transform duration-300 translate-x-full";
    panelContainer.innerHTML = `
      <div class="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-2 mb-3">
        <h3 class="font-semibold text-gray-800 dark:text-white">My Markers</h3>
        <button id="close-marker-list" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div id="marker-list-content" class="overflow-y-auto max-h-96">
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
          <i class="fas fa-map-marker-alt text-3xl mb-2"></i>
          <p>No markers added yet</p>
        </div>
      </div>
    `;

    // Add panel to the document
    document.body.appendChild(panelContainer);

    // Add event listener to close button
    const closeBtn = document.getElementById("close-marker-list");
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        toggleMarkerListPanel(false);
      });
    }
  }

  /**
   * Toggle marker list panel visibility
   */
  function toggleMarkerListPanel(forceState) {
    const panel = document.getElementById("marker-list-panel");
    const markerListBtn = document.getElementById("marker-list-btn");

    if (!panel) return;

    const isVisible = !panel.classList.contains("translate-x-full");
    const newState = forceState !== undefined ? forceState : !isVisible;

    if (newState) {
      // Show panel
      panel.classList.remove("translate-x-full");
      if (markerListBtn) markerListBtn.classList.add("bg-blue-100");

      // Update list content
      updateMarkerListContent();
    } else {
      // Hide panel
      panel.classList.add("translate-x-full");
      if (markerListBtn) markerListBtn.classList.remove("bg-blue-100");
    }
  }

  /**
   * Update marker list content
   */
  function updateMarkerListContent() {
    const listContent = document.getElementById("marker-list-content");
    if (!listContent) return;

    // Clear current content
    listContent.innerHTML = "";

    // Check if we have markers
    if (markerManager.customMarkers.length === 0) {
      listContent.innerHTML = `
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
          <i class="fas fa-map-marker-alt text-3xl mb-2"></i>
          <p>No markers added yet</p>
        </div>
      `;
      return;
    }

    // Create list of markers
    const markersList = document.createElement("ul");
    markersList.className = "space-y-2";

    markerManager.customMarkers.forEach((marker) => {
      const listItem = document.createElement("li");
      listItem.className =
        "p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md cursor-pointer transition-colors";
      listItem.innerHTML = `
        <div class="flex items-center">
          <div class="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center text-blue-600 dark:text-blue-400">
            <i class="fas fa-map-marker-alt"></i>
          </div>
          <div class="ml-3 flex-1 overflow-hidden">
            <div class="font-medium text-gray-800 dark:text-white truncate">${
              marker.title || "Unnamed Marker"
            }</div>
            <div class="text-xs text-gray-500 dark:text-gray-400 truncate">${
              marker.lat
                ? marker.lat.toFixed(6) + ", " + marker.lng.toFixed(6)
                : "No GPS data"
            }</div>
          </div>
        </div>
      `;

      // Add click event to show marker details
      listItem.addEventListener("click", () => {
        if (marker.type === "leaflet") {
          // Show marker details and fly to marker
          if (marker.leafletMarker) {
            window.leafletMap.flyTo(marker.leafletMarker.getLatLng(), 12);
            marker.leafletMarker.openPopup();
          }

          markerManager.showMarkerPopup(
            marker.id,
            marker.svgX,
            marker.svgY,
            marker.lat,
            marker.lng,
            "leaflet",
            marker.leafletMarker
          );
        }
      });

      markersList.appendChild(listItem);
    });

    listContent.appendChild(markersList);
  }

  // Make the updateMarkerListContent function available globally
  window.updateMarkerListContent = updateMarkerListContent;
});

/**
 * Map Marker Manager Class
 * Handles adding and managing custom markers on both maps
 */
class MapMarkerManager {
  constructor() {
    // State variables
    this.isMarkerMode = false;
    this.customMarkers = [];
    this.activeMarkerId = null;
    this.markerCounter = 0;

    // Get map elements
    this.svgMap = window.solarMap;
    this.leafletMap = window.leafletMap;

    // Set up event listeners
    this.setupEventListeners();

    // Load saved markers if available
    this.loadSavedMarkers();
  }

  /**
   * Set up event listeners for map interactions
   */
  setupEventListeners() {
    // Leaflet Map click event for adding markers
    if (this.leafletMap) {
      this.leafletMap.on("click", (e) => {
        if (!this.isMarkerMode) return;

        // Get the latitude and longitude
        const latlng = e.latlng;
        this.addLeafletMarker(latlng.lat, latlng.lng);
      });
    }

    // Listen for map tab changes
    const satelliteTab = document.getElementById("satellite-tab");

    if (satelliteTab) {
      satelliteTab.addEventListener("click", () => {
        this.updateMarkerVisibility("leaflet");
      });
    }
  }

  /**
   * Toggle marker mode on/off
   */
  toggleMarkerMode() {
    this.isMarkerMode = !this.isMarkerMode;

    // Update button appearance
    const addMarkerBtn = document.getElementById("add-marker-btn");
    if (addMarkerBtn) {
      if (this.isMarkerMode) {
        addMarkerBtn.classList.add("bg-blue-100");
        this.showNotification("Click on the map to add a marker", "info");
      } else {
        addMarkerBtn.classList.remove("bg-blue-100");
      }
    }

    // Set cursor style on map containers
    const leafletMapContainer = document.getElementById(
      "leaflet-map-container"
    );

    if (leafletMapContainer) {
      leafletMapContainer.style.cursor = this.isMarkerMode ? "crosshair" : "";
    }
  }

  /**
   * Add a marker to the Leaflet map
   */
  addLeafletMarker(lat, lng) {
    if (!this.leafletMap) return;

    const markerId = `custom-marker-${this.markerCounter++}`;

    // Create custom icon
    const customIcon = L.divIcon({
      className: "custom-leaflet-marker",
      html: '<i class="fas fa-map-marker-alt text-blue-600 text-2xl"></i>',
      iconSize: [30, 30],
      iconAnchor: [15, 30],
      popupAnchor: [0, -30],
    });

    // Create the marker
    const marker = L.marker([lat, lng], { icon: customIcon }).addTo(
      this.leafletMap
    );

    // Show marker popup on creation
    this.showMarkerPopup(markerId, null, null, lat, lng, "leaflet", marker);

    // Create marker data object
    const markerData = {
      id: markerId,
      svgX: null,
      svgY: null,
      lat: lat,
      lng: lng,
      title: "Custom Marker",
      note: "",
      type: "leaflet",
      leafletMarker: marker,
    };

    // Store the marker
    this.customMarkers.push(markerData);

    // Add event listener for marker click
    marker.on("click", () => {
      this.showMarkerPopup(markerId, null, null, lat, lng, "leaflet", marker);
    });

    // Save markers to localStorage
    this.saveMarkers();

    // Turn off marker mode after adding a marker
    this.toggleMarkerMode();

    // Update marker list if panel is open
    const panel = document.getElementById("marker-list-panel");
    if (panel && !panel.classList.contains("translate-x-full")) {
      window.updateMarkerListContent();
    }
  }

  /**
   * Update marker visibility based on current map type
   */
  updateMarkerVisibility(mapType) {
    // In this implementation, only Leaflet markers are shown
    // as we've hidden the Thailand SVG map
  }

  /**
   * Show marker popup for editing or viewing
   */
  showMarkerPopup(id, svgX, svgY, lat, lng, type, leafletMarker) {
    // Set active marker
    this.activeMarkerId = id;

    // Find marker data
    const markerData = this.customMarkers.find((m) => m.id === id);
    if (!markerData) return;

    // Create popup content
    const popupContent = document.createElement("div");
    popupContent.className = "marker-popup p-2";
    popupContent.innerHTML = `
      <div class="mb-3">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
        <input type="text" id="marker-title" value="${markerData.title || ""}" 
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
        >
      </div>
      <div class="mb-3">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Notes</label>
        <textarea id="marker-note" rows="3" 
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
        >${markerData.note || ""}</textarea>
      </div>
      ${
        lat && lng
          ? `<div class="text-xs text-gray-500 mb-3">
           Coordinates: ${lat.toFixed(6)}, ${lng.toFixed(6)}
         </div>`
          : ""
      }
      <div class="flex justify-between">
        <button id="delete-marker" 
          class="px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 text-sm rounded-md transition-colors">
          Delete
        </button>
        <div>
          <button id="cancel-marker" 
            class="px-3 py-1.5 bg-gray-50 text-gray-700 hover:bg-gray-100 text-sm rounded-md transition-colors mr-2">
            Cancel
          </button>
          <button id="save-marker" 
            class="px-3 py-1.5 bg-blue-600 text-white hover:bg-blue-700 text-sm rounded-md transition-colors">
            Save
          </button>
        </div>
      </div>
    `;

    // Show popup based on map type
    if (type === "leaflet" && leafletMarker) {
      leafletMarker
        .bindPopup(popupContent, {
          minWidth: 250,
          closeButton: false,
          className: "custom-popup",
        })
        .openPopup();

      // Add event listeners after the popup is opened
      leafletMarker.on("popupopen", () => {
        this.addPopupEventListeners(id, leafletMarker);
      });
    }
  }

  /**
   * Add event listeners to marker popup
   */
  addPopupEventListeners(markerId, leafletMarker) {
    // Get popup elements
    const deleteBtn = document.getElementById("delete-marker");
    const cancelBtn = document.getElementById("cancel-marker");
    const saveBtn = document.getElementById("save-marker");
    const titleInput = document.getElementById("marker-title");
    const noteInput = document.getElementById("marker-note");

    if (!deleteBtn || !cancelBtn || !saveBtn || !titleInput || !noteInput)
      return;

    // Delete marker
    deleteBtn.addEventListener("click", () => {
      this.deleteMarker(markerId);
      if (leafletMarker) {
        leafletMarker.closePopup();
        this.leafletMap.removeLayer(leafletMarker);
      }
    });

    // Cancel editing
    cancelBtn.addEventListener("click", () => {
      if (leafletMarker) {
        leafletMarker.closePopup();
      }
    });

    // Save marker changes
    saveBtn.addEventListener("click", () => {
      this.updateMarker(
        markerId,
        titleInput.value.trim(),
        noteInput.value.trim()
      );
      if (leafletMarker) {
        leafletMarker.closePopup();
      }
    });
  }

  /**
   * Update marker data
   */
  updateMarker(id, title, note) {
    const markerIndex = this.customMarkers.findIndex((m) => m.id === id);
    if (markerIndex === -1) return;

    // Update marker data
    this.customMarkers[markerIndex].title = title || "Custom Marker";
    this.customMarkers[markerIndex].note = note || "";

    // Save changes
    this.saveMarkers();

    // Update marker list if visible
    const panel = document.getElementById("marker-list-panel");
    if (panel && !panel.classList.contains("translate-x-full")) {
      window.updateMarkerListContent();
    }

    // Show success notification
    this.showNotification("Marker updated successfully", "success");
  }

  /**
   * Delete a marker
   */
  deleteMarker(id) {
    const markerIndex = this.customMarkers.findIndex((m) => m.id === id);
    if (markerIndex === -1) return;

    // Remove from array
    this.customMarkers.splice(markerIndex, 1);

    // Save changes
    this.saveMarkers();

    // Update marker list if visible
    const panel = document.getElementById("marker-list-panel");
    if (panel && !panel.classList.contains("translate-x-full")) {
      window.updateMarkerListContent();
    }

    // Show notification
    this.showNotification("Marker deleted", "info");
  }

  /**
   * Save markers to localStorage
   */
  saveMarkers() {
    if (!window.localStorage) return;

    // Create serializable version of markers (without leafletMarker instances)
    const markersToSave = this.customMarkers.map((marker) => {
      const { leafletMarker, ...serializableMarker } = marker;
      return serializableMarker;
    });

    localStorage.setItem("customMapMarkers", JSON.stringify(markersToSave));
  }

  /**
   * Load saved markers from localStorage
   */
  loadSavedMarkers() {
    if (!window.localStorage) return;

    try {
      const savedMarkers = localStorage.getItem("customMapMarkers");
      if (!savedMarkers) return;

      const parsedMarkers = JSON.parse(savedMarkers);
      if (!Array.isArray(parsedMarkers)) return;

      // Restore markers on appropriate maps
      parsedMarkers.forEach((marker) => {
        // Only restore Leaflet markers since Thailand map is hidden
        if (marker.type === "leaflet" && marker.lat && marker.lng) {
          // Create the marker on Leaflet map
          const customIcon = L.divIcon({
            className: "custom-leaflet-marker",
            html: '<i class="fas fa-map-marker-alt text-blue-600 text-2xl"></i>',
            iconSize: [30, 30],
            iconAnchor: [15, 30],
            popupAnchor: [0, -30],
          });

          const leafletMarker = L.marker([marker.lat, marker.lng], {
            icon: customIcon,
          }).addTo(this.leafletMap);

          // Add click event
          leafletMarker.on("click", () => {
            this.showMarkerPopup(
              marker.id,
              marker.svgX,
              marker.svgY,
              marker.lat,
              marker.lng,
              "leaflet",
              leafletMarker
            );
          });

          // Add leaflet marker instance to the data
          this.customMarkers.push({
            ...marker,
            leafletMarker,
          });
        }
      });

      // Ensure counter is set correctly to avoid ID conflicts
      if (parsedMarkers.length > 0) {
        const maxId = Math.max(
          ...parsedMarkers.map((m) => {
            const idNum = parseInt(m.id.replace("custom-marker-", ""));
            return isNaN(idNum) ? 0 : idNum;
          })
        );
        this.markerCounter = maxId + 1;
      }
    } catch (error) {
      console.error("Error loading saved markers:", error);
    }
  }

  /**
   * Show notification
   */
  showNotification(message, type = "info") {
    if (typeof window.showNotification === "function") {
      window.showNotification(message, type);
    } else {
      // Fallback if notification system is not available
      console.log(`[${type.toUpperCase()}] ${message}`);
    }
  }
}
