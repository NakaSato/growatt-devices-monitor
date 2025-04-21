/**
 * Map Interaction Handler
 * Enhances the interactive features of the solar plant maps
 */
class MapInteractionHandler {
  constructor(mapInstance, options = {}) {
    this.map = mapInstance;
    this.options = {
      highlightDuration: 500,
      animationEnabled: true,
      tooltipDelay: 200,
      enableKeyboardNavigation: true,
      ...options,
    };

    this.selectedPlant = null;
    this.tooltipTimer = null;
    this.init();
  }

  init() {
    this.setupInteractions();
    if (this.options.enableKeyboardNavigation) {
      this.setupKeyboardNavigation();
    }
  }

  setupInteractions() {
    // Add hover effects for plant markers
    document.querySelectorAll(".plant-marker").forEach((marker) => {
      marker.addEventListener("mouseenter", () => {
        this.highlightMarker(marker);
      });

      marker.addEventListener("mouseleave", () => {
        if (marker !== this.selectedPlant) {
          this.unhighlightMarker(marker);
        }
      });

      marker.addEventListener("click", (e) => {
        this.selectPlant(marker, e);
      });
    });

    // Add region interactions if they exist
    document.querySelectorAll(".svg-region").forEach((region) => {
      region.addEventListener("mouseenter", () => {
        region.classList.add("svg-hover");

        // Show region stats if available
        const regionId =
          region.getAttribute("id") || region.getAttribute("data-id");
        if (regionId && this.options.showRegionStats) {
          this.showRegionStats(regionId, region);
        }
      });

      region.addEventListener("mouseleave", () => {
        if (!region.classList.contains("svg-active")) {
          region.classList.remove("svg-hover");
        }
        this.hideRegionStats();
      });
    });
  }

  setupKeyboardNavigation() {
    document.addEventListener("keydown", (e) => {
      // Escape key to reset view
      if (e.key === "Escape") {
        this.map.resetView();
      }

      // Tab navigation between plants
      if (e.key === "Tab" && this.map.plants && this.map.plants.length > 0) {
        e.preventDefault();

        let currentIndex = -1;
        if (this.selectedPlant) {
          currentIndex = this.map.plants.findIndex(
            (p) =>
              p.element === this.selectedPlant ||
              p.id === this.selectedPlant.getAttribute("data-plant-id")
          );
        }

        // Move to next plant
        const nextIndex = e.shiftKey
          ? currentIndex <= 0
            ? this.map.plants.length - 1
            : currentIndex - 1
          : currentIndex >= this.map.plants.length - 1
          ? 0
          : currentIndex + 1;

        const nextPlant = this.map.plants[nextIndex];
        if (nextPlant && nextPlant.element) {
          this.selectPlant(nextPlant.element);

          // Center view on the selected plant
          this.map.panTo(nextPlant.coordinates.x, nextPlant.coordinates.y);
        }
      }
    });
  }

  highlightMarker(marker) {
    marker.classList.add("highlight");

    if (this.options.animationEnabled) {
      // Add pulse animation
      const circle = marker.querySelector("circle");
      if (circle) {
        circle.classList.add("svg-pulse");
      }
    }

    // Show tooltip with delay
    clearTimeout(this.tooltipTimer);
    this.tooltipTimer = setTimeout(() => {
      const plantId = marker.getAttribute("data-plant-id");
      const plant = this.map.plants.find((p) => p.id === plantId);
      if (plant) {
        this.map.showTooltip(plant, plant.coordinates);
      }
    }, this.options.tooltipDelay);
  }

  unhighlightMarker(marker) {
    marker.classList.remove("highlight");

    if (this.options.animationEnabled) {
      const circle = marker.querySelector("circle");
      if (circle) {
        circle.classList.remove("svg-pulse");
      }
    }

    // Cancel tooltip display
    clearTimeout(this.tooltipTimer);
    this.map.hideTooltip();
  }

  selectPlant(marker, event) {
    // Clear previous selection
    if (this.selectedPlant) {
      this.selectedPlant.classList.remove("selected");
    }

    // Set new selection
    marker.classList.add("selected");
    this.selectedPlant = marker;

    // Get plant data and dispatch selection event
    const plantId = marker.getAttribute("data-plant-id");
    const plant = this.map.plants.find((p) => p.id === plantId);

    if (plant) {
      // Dispatch custom event
      const customEvent = new CustomEvent("plant-selected", {
        detail: plant,
      });
      document.dispatchEvent(customEvent);

      // Animate to center the selected plant
      if (this.options.animationEnabled) {
        this.map.panToAnimated(plant.coordinates.x, plant.coordinates.y);
      }
    }

    // Stop propagation if this was triggered by a click event
    if (event) {
      event.stopPropagation();
    }
  }

  showRegionStats(regionId, regionElement) {
    // Create region tooltip
    const tooltip = document.createElement("div");
    tooltip.className = "svg-tooltip region-tooltip";

    // Fetch region data (simulate API call)
    const regionData = this.getRegionData(regionId);

    tooltip.innerHTML = `
      <div class="tooltip-title">${regionData.name}</div>
      <div class="tooltip-content">
        <div>Plants: ${regionData.plantCount}</div>
        <div>Total Capacity: ${regionData.totalCapacity} kW</div>
        <div>Avg Performance: ${regionData.avgPerformance}%</div>
      </div>
    `;

    // Position tooltip near region
    const rect = regionElement.getBoundingClientRect();
    const mapRect = this.map.container.getBoundingClientRect();

    tooltip.style.position = "absolute";
    tooltip.style.left = `${rect.left - mapRect.left + rect.width / 2}px`;
    tooltip.style.top = `${rect.top - mapRect.top - 100}px`;

    this.map.container.appendChild(tooltip);
    this.regionTooltip = tooltip;
  }

  hideRegionStats() {
    if (this.regionTooltip) {
      this.regionTooltip.remove();
      this.regionTooltip = null;
    }
  }

  // Mock method to get region data (would be replaced with actual API call)
  getRegionData(regionId) {
    // Simulated data for demo purposes
    const regionStats = {
      north: {
        name: "Northern Thailand",
        plantCount: 12,
        totalCapacity: 235,
        avgPerformance: 87,
      },
      northeast: {
        name: "Northeastern Thailand",
        plantCount: 8,
        totalCapacity: 175,
        avgPerformance: 82,
      },
      central: {
        name: "Central Thailand",
        plantCount: 15,
        totalCapacity: 310,
        avgPerformance: 91,
      },
      east: {
        name: "Eastern Thailand",
        plantCount: 7,
        totalCapacity: 145,
        avgPerformance: 88,
      },
      west: {
        name: "Western Thailand",
        plantCount: 5,
        totalCapacity: 95,
        avgPerformance: 85,
      },
      south: {
        name: "Southern Thailand",
        plantCount: 10,
        totalCapacity: 180,
        avgPerformance: 83,
      },
    };

    return (
      regionStats[regionId] || {
        name: `Region ${regionId}`,
        plantCount: 0,
        totalCapacity: 0,
        avgPerformance: 0,
      }
    );
  }
}

// Export the class
if (typeof module !== "undefined" && module.exports) {
  module.exports = MapInteractionHandler;
} else {
  window.MapInteractionHandler = MapInteractionHandler;
}
