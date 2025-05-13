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
        if (marker.type === "svg") {
          // Switch to Thailand map if needed
          const thailandTab = document.getElementById("thailand-tab");
          if (
            thailandTab &&
            document
              .getElementById("thailand-map-container")
              .classList.contains("hidden")
          ) {
            thailandTab.click();
          }

          // Show marker details
          markerManager.showMarkerPopup(
            marker.id,
            marker.svgX,
            marker.svgY,
            marker.lat,
            marker.lng,
            "svg"
          );
        } else if (marker.type === "leaflet") {
          // Switch to Leaflet map if needed
          const satelliteTab = document.getElementById("satellite-tab");
          if (
            satelliteTab &&
            document
              .getElementById("leaflet-map-container")
              .classList.contains("hidden")
          ) {
            satelliteTab.click();
          }

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
    // SVG Map click event for adding markers
    const thailandMapContainer = document.getElementById(
      "thailand-map-container"
    );
    if (thailandMapContainer) {
      thailandMapContainer.addEventListener("click", (e) => {
        if (!this.isMarkerMode) return;

        // Get the SVG point
        const svgElement = thailandMapContainer.querySelector("svg");
        if (svgElement) {
          const point = this.getSVGPoint(e, svgElement);
          this.addSVGMarker(point.x, point.y);
        }
      });
    }

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
    const thailandTab = document.getElementById("thailand-tab");
    const satelliteTab = document.getElementById("satellite-tab");

    if (thailandTab) {
      thailandTab.addEventListener("click", () => {
        this.updateMarkerVisibility("svg");
      });
    }

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
    const thailandMapContainer = document.getElementById(
      "thailand-map-container"
    );
    const leafletMapContainer = document.getElementById(
      "leaflet-map-container"
    );

    if (thailandMapContainer) {
      thailandMapContainer.style.cursor = this.isMarkerMode ? "crosshair" : "";
    }

    if (leafletMapContainer) {
      leafletMapContainer.style.cursor = this.isMarkerMode ? "crosshair" : "";
    }
  }

  /**
   * Add a marker to the SVG map
   */
  addSVGMarker(x, y) {
    if (!this.svgMap) return;

    const markerId = `custom-marker-${this.markerCounter++}`;
    const svgContainer = document.querySelector("#thailand-map-container svg");

    if (!svgContainer) return;

    // Create the marker group
    const markerGroup = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "g"
    );
    markerGroup.setAttribute("class", "custom-marker");
    markerGroup.setAttribute("id", markerId);
    markerGroup.setAttribute("transform", `translate(${x}, ${y})`);

    // Create the marker path (using pin shape)
    const markerPath = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "path"
    );
    markerPath.setAttribute(
      "d",
      "M0,0 C-6,-20 6,-20 0,0 M0,-15 a6,6 0 1,0 0.001,0"
    );
    markerPath.setAttribute("fill", "#3b82f6"); // Blue color
    markerPath.setAttribute("stroke", "#1d4ed8");
    markerPath.setAttribute("stroke-width", "1");

    // Add event listeners for marker interaction
    markerGroup.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent adding new markers when clicking existing ones
      this.showMarkerPopup(markerId, x, y, null, null, "svg");
    });

    // Add the marker to the SVG
    markerGroup.appendChild(markerPath);
    svgContainer.appendChild(markerGroup);

    // Create marker data object
    const markerData = {
      id: markerId,
      svgX: x,
      svgY: y,
      lat: null,
      lng: null,
      title: "Custom Marker",
      note: "",
      type: "svg",
    };

    // Try to convert SVG coordinates to lat/lng if possible
    if (this.svgMap && typeof this.svgMap.svgToGpsCoordinates === "function") {
      const gpsCoords = this.svgMap.svgToGpsCoordinates(x, y);
      if (gpsCoords) {
        markerData.lat = gpsCoords.lat;
        markerData.lng = gpsCoords.lng;
      }
    }

    this.customMarkers.push(markerData);
    this.saveMarkers();

    // Show popup to add details
    this.showMarkerPopup(markerId, x, y, null, null, "svg");

    // Exit marker mode after adding
    this.toggleMarkerMode();
  }

  /**
   * Add a marker to the Leaflet map
   */
  addLeafletMarker(lat, lng) {
    if (!this.leafletMap) return;

    const markerId = `custom-marker-${this.markerCounter++}`;

    // Create Leaflet marker
    const marker = L.marker([lat, lng], {
      draggable: true,
      title: "Custom Marker",
    }).addTo(this.leafletMap);

    // Add popup
    marker.on("click", () => {
      this.showMarkerPopup(markerId, null, null, lat, lng, "leaflet", marker);
    });

    // Handle drag end to update position
    marker.on("dragend", () => {
      const newPosition = marker.getLatLng();
      this.updateMarkerPosition(
        markerId,
        null,
        null,
        newPosition.lat,
        newPosition.lng
      );
    });

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

    // Try to convert lat/lng to SVG coordinates if possible
    if (this.svgMap && typeof this.svgMap.gpsToSvgCoordinates === "function") {
      const svgCoords = this.svgMap.gpsToSvgCoordinates(lat, lng);
      if (svgCoords) {
        markerData.svgX = svgCoords.x;
        markerData.svgY = svgCoords.y;
      }
    }

    this.customMarkers.push(markerData);
    this.saveMarkers();

    // Show popup to add details
    this.showMarkerPopup(markerId, null, null, lat, lng, "leaflet", marker);

    // Exit marker mode after adding
    this.toggleMarkerMode();
  }

  /**
   * Show marker popup for editing details
   */
  showMarkerPopup(markerId, svgX, svgY, lat, lng, type, leafletMarker = null) {
    // Find the marker data
    const markerData = this.customMarkers.find(
      (marker) => marker.id === markerId
    );
    if (!markerData) return;

    // Create popup container
    const popup = document.createElement("div");
    popup.className =
      "fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50";
    popup.id = "marker-popup";

    // Create popup content
    popup.innerHTML = `
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-5 max-w-md w-full mx-4">
        <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4">Marker Details</h3>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title</label>
            <input type="text" id="marker-title" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500" value="${
              markerData.title || ""
            }">
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Notes</label>
            <textarea id="marker-note" rows="3" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">${
              markerData.note || ""
            }</textarea>
          </div>
          
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Latitude</label>
              <input type="text" id="marker-lat" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500" value="${
                markerData.lat || ""
              }" ${type === "svg" ? "" : "readonly"}>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Longitude</label>
              <input type="text" id="marker-lng" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500" value="${
                markerData.lng || ""
              }" ${type === "svg" ? "" : "readonly"}>
            </div>
          </div>
          
          <div class="flex justify-between pt-4">
            <button id="delete-marker" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500">Delete</button>
            <div class="space-x-2">
              <button id="cancel-marker" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400">Cancel</button>
              <button id="save-marker" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">Save</button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Add popup to the document
    document.body.appendChild(popup);

    // Set active marker ID
    this.activeMarkerId = markerId;

    // Add event listeners
    document.getElementById("save-marker").addEventListener("click", () => {
      const title = document.getElementById("marker-title").value;
      const note = document.getElementById("marker-note").value;
      let updatedLat = markerData.lat;
      let updatedLng = markerData.lng;

      // Get lat/lng values if editable
      if (type === "svg") {
        updatedLat = parseFloat(document.getElementById("marker-lat").value);
        updatedLng = parseFloat(document.getElementById("marker-lng").value);
      }

      // Update marker data
      this.updateMarkerDetails(markerId, title, note, updatedLat, updatedLng);
      this.closePopup();
    });

    document.getElementById("cancel-marker").addEventListener("click", () => {
      this.closePopup();
    });

    document.getElementById("delete-marker").addEventListener("click", () => {
      this.deleteMarker(markerId);
      this.closePopup();
    });
  }

  /**
   * Update marker details
   */
  updateMarkerDetails(markerId, title, note, lat, lng) {
    const markerIndex = this.customMarkers.findIndex(
      (marker) => marker.id === markerId
    );
    if (markerIndex === -1) return;

    // Update the marker data
    this.customMarkers[markerIndex].title = title;
    this.customMarkers[markerIndex].note = note;

    // Update coordinates if provided
    if (lat !== null && !isNaN(lat)) this.customMarkers[markerIndex].lat = lat;
    if (lng !== null && !isNaN(lng)) this.customMarkers[markerIndex].lng = lng;

    // If this is a Leaflet marker and the coordinates changed, update the marker position
    if (
      this.customMarkers[markerIndex].type === "leaflet" &&
      this.customMarkers[markerIndex].leafletMarker &&
      lat !== null &&
      lng !== null
    ) {
      this.customMarkers[markerIndex].leafletMarker.setLatLng([lat, lng]);
    }

    // If SVG marker, update SVG coordinates if needed
    if (
      this.customMarkers[markerIndex].type === "svg" &&
      lat !== null &&
      lng !== null
    ) {
      if (
        this.svgMap &&
        typeof this.svgMap.gpsToSvgCoordinates === "function"
      ) {
        const svgCoords = this.svgMap.gpsToSvgCoordinates(lat, lng);
        if (svgCoords) {
          this.customMarkers[markerIndex].svgX = svgCoords.x;
          this.customMarkers[markerIndex].svgY = svgCoords.y;

          // Update SVG marker position
          const markerElement = document.getElementById(markerId);
          if (markerElement) {
            markerElement.setAttribute(
              "transform",
              `translate(${svgCoords.x}, ${svgCoords.y})`
            );
          }
        }
      }
    }

    // Save updated markers
    this.saveMarkers();

    // Update the marker list if it's open
    if (
      document.getElementById("marker-list-panel") &&
      !document
        .getElementById("marker-list-panel")
        .classList.contains("translate-x-full")
    ) {
      // Use a function in the global scope
      if (typeof window.updateMarkerListContent === "function") {
        window.updateMarkerListContent();
      }
    }
  }

  /**
   * Update marker position after drag
   */
  updateMarkerPosition(markerId, svgX, svgY, lat, lng) {
    const markerIndex = this.customMarkers.findIndex(
      (marker) => marker.id === markerId
    );
    if (markerIndex === -1) return;

    // Update coordinates
    if (svgX !== null) this.customMarkers[markerIndex].svgX = svgX;
    if (svgY !== null) this.customMarkers[markerIndex].svgY = svgY;
    if (lat !== null) this.customMarkers[markerIndex].lat = lat;
    if (lng !== null) this.customMarkers[markerIndex].lng = lng;

    // If it's a Leaflet marker and we have SVG coordinates, update them based on new lat/lng
    if (
      this.customMarkers[markerIndex].type === "leaflet" &&
      lat !== null &&
      lng !== null
    ) {
      if (
        this.svgMap &&
        typeof this.svgMap.gpsToSvgCoordinates === "function"
      ) {
        const svgCoords = this.svgMap.gpsToSvgCoordinates(lat, lng);
        if (svgCoords) {
          this.customMarkers[markerIndex].svgX = svgCoords.x;
          this.customMarkers[markerIndex].svgY = svgCoords.y;
        }
      }
    }

    // If it's an SVG marker and we have lat/lng, update them based on new SVG coordinates
    if (
      this.customMarkers[markerIndex].type === "svg" &&
      svgX !== null &&
      svgY !== null
    ) {
      if (
        this.svgMap &&
        typeof this.svgMap.svgToGpsCoordinates === "function"
      ) {
        const gpsCoords = this.svgMap.svgToGpsCoordinates(svgX, svgY);
        if (gpsCoords) {
          this.customMarkers[markerIndex].lat = gpsCoords.lat;
          this.customMarkers[markerIndex].lng = gpsCoords.lng;
        }
      }
    }

    // Save updated markers
    this.saveMarkers();

    // Update the marker list if it's open
    if (
      document.getElementById("marker-list-panel") &&
      !document
        .getElementById("marker-list-panel")
        .classList.contains("translate-x-full")
    ) {
      // Use a function in the global scope
      if (typeof window.updateMarkerListContent === "function") {
        window.updateMarkerListContent();
      }
    }
  }

  /**
   * Delete a marker
   */
  deleteMarker(markerId) {
    const markerIndex = this.customMarkers.findIndex(
      (marker) => marker.id === markerId
    );
    if (markerIndex === -1) return;

    // Remove from DOM based on type
    if (this.customMarkers[markerIndex].type === "svg") {
      const markerElement = document.getElementById(markerId);
      if (markerElement) markerElement.remove();
    } else if (this.customMarkers[markerIndex].type === "leaflet") {
      if (this.customMarkers[markerIndex].leafletMarker) {
        this.leafletMap.removeLayer(
          this.customMarkers[markerIndex].leafletMarker
        );
      }
    }

    // Remove from array
    this.customMarkers.splice(markerIndex, 1);

    // Save updated markers
    this.saveMarkers();

    // Update the marker list if it's open
    if (
      document.getElementById("marker-list-panel") &&
      !document
        .getElementById("marker-list-panel")
        .classList.contains("translate-x-full")
    ) {
      // Use a function in the global scope
      if (typeof window.updateMarkerListContent === "function") {
        window.updateMarkerListContent();
      }
    }

    this.showNotification("Marker deleted", "success");
  }

  /**
   * Close the marker popup
   */
  closePopup() {
    const popup = document.getElementById("marker-popup");
    if (popup) popup.remove();
    this.activeMarkerId = null;
  }

  /**
   * Get SVG point from mouse event
   */
  getSVGPoint(event, svgElement) {
    // Get the SVG point from a mouse event
    const pt = svgElement.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;

    // Convert to SVG coordinates
    const svgP = pt.matrixTransform(svgElement.getScreenCTM().inverse());
    return svgP;
  }

  /**
   * Save markers to localStorage
   */
  saveMarkers() {
    try {
      // Convert markers to serializable format (remove Leaflet marker references)
      const markersToSave = this.customMarkers.map((marker) => {
        const { leafletMarker, ...serializable } = marker;
        return serializable;
      });

      localStorage.setItem("customMapMarkers", JSON.stringify(markersToSave));
    } catch (error) {
      console.error("Error saving markers:", error);
    }
  }

  /**
   * Load saved markers from localStorage
   */
  loadSavedMarkers() {
    try {
      const savedMarkers = localStorage.getItem("customMapMarkers");
      if (savedMarkers) {
        const parsedMarkers = JSON.parse(savedMarkers);

        // Set the counter to the highest ID + 1
        const ids = parsedMarkers
          .map((marker) => {
            const match = marker.id.match(/custom-marker-(\d+)/);
            return match ? parseInt(match[1], 10) : 0;
          })
          .filter((id) => !isNaN(id));

        this.markerCounter = ids.length > 0 ? Math.max(...ids) + 1 : 0;

        // Add each marker to the appropriate map
        parsedMarkers.forEach((marker) => {
          if (marker.type === "svg") {
            this.restoreSVGMarker(marker);
          } else if (marker.type === "leaflet") {
            this.restoreLeafletMarker(marker);
          }
        });
      }
    } catch (error) {
      console.error("Error loading markers:", error);
    }
  }

  /**
   * Restore an SVG marker from saved data
   */
  restoreSVGMarker(markerData) {
    if (!markerData.svgX || !markerData.svgY) return;

    const svgContainer = document.querySelector("#thailand-map-container svg");
    if (!svgContainer) return;

    // Create the marker group
    const markerGroup = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "g"
    );
    markerGroup.setAttribute("class", "custom-marker");
    markerGroup.setAttribute("id", markerData.id);
    markerGroup.setAttribute(
      "transform",
      `translate(${markerData.svgX}, ${markerData.svgY})`
    );

    // Create the marker path
    const markerPath = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "path"
    );
    markerPath.setAttribute(
      "d",
      "M0,0 C-6,-20 6,-20 0,0 M0,-15 a6,6 0 1,0 0.001,0"
    );
    markerPath.setAttribute("fill", "#3b82f6");
    markerPath.setAttribute("stroke", "#1d4ed8");
    markerPath.setAttribute("stroke-width", "1");

    // Add event listeners for marker interaction
    markerGroup.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent adding new markers when clicking existing ones
      this.showMarkerPopup(
        markerData.id,
        markerData.svgX,
        markerData.svgY,
        markerData.lat,
        markerData.lng,
        "svg"
      );
    });

    // Add the marker to the SVG
    markerGroup.appendChild(markerPath);
    svgContainer.appendChild(markerGroup);

    // Store the marker in our array
    this.customMarkers.push({
      ...markerData,
      leafletMarker: null,
    });

    // Hide if we're on the wrong map type
    if (
      document
        .getElementById("thailand-map-container")
        .classList.contains("hidden")
    ) {
      markerGroup.style.display = "none";
    }
  }

  /**
   * Restore a Leaflet marker from saved data
   */
  restoreLeafletMarker(markerData) {
    if (!this.leafletMap || !markerData.lat || !markerData.lng) return;

    // Create Leaflet marker
    const marker = L.marker([markerData.lat, markerData.lng], {
      draggable: true,
      title: markerData.title || "Custom Marker",
    });

    // Only add to map if Leaflet map is visible
    if (
      !document
        .getElementById("leaflet-map-container")
        .classList.contains("hidden")
    ) {
      marker.addTo(this.leafletMap);
    }

    // Add popup
    marker.on("click", () => {
      this.showMarkerPopup(
        markerData.id,
        markerData.svgX,
        markerData.svgY,
        markerData.lat,
        markerData.lng,
        "leaflet",
        marker
      );
    });

    // Handle drag end to update position
    marker.on("dragend", () => {
      const newPosition = marker.getLatLng();
      this.updateMarkerPosition(
        markerData.id,
        null,
        null,
        newPosition.lat,
        newPosition.lng
      );
    });

    // Store the marker in our array
    this.customMarkers.push({
      ...markerData,
      leafletMarker: marker,
    });
  }

  /**
   * Update marker visibility based on active map
   */
  updateMarkerVisibility(activeMapType) {
    this.customMarkers.forEach((marker) => {
      if (marker.type === "svg") {
        const markerElement = document.getElementById(marker.id);
        if (markerElement) {
          markerElement.style.display = activeMapType === "svg" ? "" : "none";
        }
      } else if (marker.type === "leaflet" && marker.leafletMarker) {
        if (activeMapType === "leaflet") {
          if (!this.leafletMap.hasLayer(marker.leafletMarker)) {
            marker.leafletMarker.addTo(this.leafletMap);
          }
        } else {
          if (this.leafletMap.hasLayer(marker.leafletMarker)) {
            this.leafletMap.removeLayer(marker.leafletMarker);
          }
        }
      }
    });
  }

  /**
   * Show notification
   */
  showNotification(message, type = "info") {
    // Try to use existing notification function
    if (typeof window.showNotification === "function") {
      window.showNotification(message, type);
      return;
    }

    // Fallback notification implementation
    const notification = document.createElement("div");
    notification.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
      type === "success"
        ? "bg-green-500 text-white"
        : type === "error"
        ? "bg-red-500 text-white"
        : type === "warning"
        ? "bg-yellow-500 text-white"
        : "bg-blue-500 text-white"
    }`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      notification.classList.add(
        "opacity-0",
        "transform",
        "translate-y-2",
        "transition-all",
        "duration-500"
      );
      setTimeout(() => notification.remove(), 500);
    }, 3000);
  }
}
