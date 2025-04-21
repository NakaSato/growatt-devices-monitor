/**
 * Thailand Map Hover Enhancer
 * Adds enhanced interactive hover features to the Thailand Solar Map
 *
 * This module enhances the existing map implementation without disrupting it,
 * adding hover regions, tooltips, and visual effects in a modular way.
 */
class ThailandMapHoverEnhancer {
  constructor(solarMapInstance, options = {}) {
    this.map = solarMapInstance;
    this.options = {
      hoverClass: "region-hover",
      activeClass: "region-active",
      tooltipClass: "region-tooltip",
      enableRegionHighlight: true,
      enableProvinceStats: true,
      enableHoverAnimation: true,
      hoverAnimationDuration: 300,
      ...options,
    };

    this.hoveredRegion = null;
    this.regionData = {};
    this.tooltipElement = null;

    this.init();
  }

  init() {
    if (!this.map) {
      console.error("ThailandMapHoverEnhancer: No valid map instance provided");
      return;
    }

    // Create tooltip container if it doesn't exist
    this.createTooltipContainer();

    // Wait for map to be fully loaded
    this.waitForMapElements().then(() => {
      this.setupRegionInteractions();
      this.loadRegionData();
    });
  }

  waitForMapElements() {
    return new Promise((resolve) => {
      const checkElements = () => {
        if (
          this.map.mapGroup &&
          this.map.mapGroup.querySelectorAll("path").length > 0
        ) {
          resolve();
        } else {
          setTimeout(checkElements, 100);
        }
      };
      checkElements();
    });
  }

  createTooltipContainer() {
    this.tooltipElement = document.createElement("div");
    this.tooltipElement.className = this.options.tooltipClass;
    this.tooltipElement.style.position = "absolute";
    this.tooltipElement.style.display = "none";
    this.tooltipElement.style.pointerEvents = "none";
    this.tooltipElement.style.zIndex = "1000";
    document.body.appendChild(this.tooltipElement);
  }

  setupRegionInteractions() {
    // Get all province/region paths
    const paths = this.map.mapGroup.querySelectorAll("path");

    paths.forEach((path) => {
      // Skip paths that aren't provinces/regions
      if (!path.id || !path.id.startsWith("TH-")) return;

      // Add ARIA attributes for accessibility
      path.setAttribute("role", "button");
      path.setAttribute("tabindex", "0");
      path.setAttribute("aria-label", `Province ${path.id.replace("TH-", "")}`);

      // Add class for styling
      path.classList.add("svg-region");

      // Mouse events
      path.addEventListener("mouseenter", (e) =>
        this.handleRegionHover(e, path)
      );
      path.addEventListener("mouseleave", (e) =>
        this.handleRegionLeave(e, path)
      );
      path.addEventListener("mousemove", (e) => this.updateTooltipPosition(e));
      path.addEventListener("click", (e) => this.handleRegionClick(e, path));

      // Keyboard events for accessibility
      path.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          this.handleRegionClick(e, path);
          e.preventDefault();
        }
      });

      // Touch events for mobile
      path.addEventListener("touchstart", (e) => {
        this.handleRegionHover(e, path);
        // Don't prevent default to allow scrolling
      });
    });
  }

  handleRegionHover(event, region) {
    this.hoveredRegion = region;

    if (this.options.enableRegionHighlight) {
      region.classList.add(this.options.hoverClass);

      if (this.options.enableHoverAnimation) {
        // Add subtle animation
        region.style.transition = `fill-opacity ${this.options.hoverAnimationDuration}ms ease`;
        region.style.fillOpacity = "0.9";
      }
    }

    // Show tooltip with region data
    if (this.options.enableProvinceStats) {
      this.showRegionTooltip(event, region);
    }

    // Dispatch custom event
    const customEvent = new CustomEvent("region-hover", {
      detail: {
        regionId: region.id,
        regionElement: region,
        originalEvent: event,
      },
    });
    document.dispatchEvent(customEvent);
  }

  handleRegionLeave(event, region) {
    if (this.hoveredRegion === region) {
      this.hoveredRegion = null;
    }

    if (this.options.enableRegionHighlight) {
      region.classList.remove(this.options.hoverClass);

      if (this.options.enableHoverAnimation) {
        // Reset styles
        region.style.transition = "";
        region.style.fillOpacity = "";
      }
    }

    // Hide tooltip
    this.hideRegionTooltip();

    // Dispatch custom event
    const customEvent = new CustomEvent("region-leave", {
      detail: {
        regionId: region.id,
        regionElement: region,
        originalEvent: event,
      },
    });
    document.dispatchEvent(customEvent);
  }

  handleRegionClick(event, region) {
    // Toggle active class
    const wasActive = region.classList.contains(this.options.activeClass);

    // Clear all active regions
    const activePaths = this.map.mapGroup.querySelectorAll(
      `.${this.options.activeClass}`
    );
    activePaths.forEach((path) =>
      path.classList.remove(this.options.activeClass)
    );

    // Set active if wasn't already active
    if (!wasActive) {
      region.classList.add(this.options.activeClass);
    }

    // Get plants in this region
    const regionPlants = this.getRegionPlants(region.id);

    // Dispatch custom event with region data and plants
    const customEvent = new CustomEvent("region-selected", {
      detail: {
        regionId: region.id,
        regionElement: region,
        regionData: this.regionData[region.id] || {},
        plants: regionPlants,
        isActive: !wasActive,
        originalEvent: event,
      },
    });
    document.dispatchEvent(customEvent);
  }

  showRegionTooltip(event, region) {
    if (!this.tooltipElement) return;

    // Get region data
    const regionId = region.id;
    const regionInfo = this.regionData[regionId] || {
      name: this.getProvinceNameFromId(regionId),
      plantCount: this.getRegionPlants(regionId).length,
      totalCapacity: this.calculateRegionCapacity(regionId),
    };

    // Populate tooltip content
    this.tooltipElement.innerHTML = `
      <div class="tooltip-title">${regionInfo.name}</div>
      <div class="tooltip-content">
        <div>Solar Plants: ${regionInfo.plantCount}</div>
        <div>Total Capacity: ${regionInfo.totalCapacity.toFixed(1)} kW</div>
        ${
          regionInfo.activeCount
            ? `<div>Active Plants: ${regionInfo.activeCount}</div>`
            : ""
        }
      </div>
    `;

    // Show tooltip
    this.tooltipElement.style.display = "block";
    this.updateTooltipPosition(event);
  }

  updateTooltipPosition(event) {
    if (!this.tooltipElement || this.tooltipElement.style.display === "none")
      return;

    // Position the tooltip near the cursor
    const padding = 15;
    let left = event.clientX + padding;
    let top = event.clientY + padding;

    // Adjust position to ensure tooltip stays within viewport
    const tooltipRect = this.tooltipElement.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    if (left + tooltipRect.width > viewportWidth) {
      left = event.clientX - tooltipRect.width - padding;
    }

    if (top + tooltipRect.height > viewportHeight) {
      top = event.clientY - tooltipRect.height - padding;
    }

    this.tooltipElement.style.left = `${left}px`;
    this.tooltipElement.style.top = `${top}px`;
  }

  hideRegionTooltip() {
    if (this.tooltipElement) {
      this.tooltipElement.style.display = "none";
    }
  }

  loadRegionData() {
    // This would typically fetch data from an API
    // For now, we'll generate data based on the existing plants

    // Prepare a mapping of regions to plants
    const regionsPlants = {};

    // Go through all plants and group by region
    this.map.plants.forEach((plant) => {
      // Determine which region this plant belongs to
      const regionId = this.findRegionForCoordinates(
        plant.latitude,
        plant.longitude
      );

      if (regionId) {
        if (!regionsPlants[regionId]) {
          regionsPlants[regionId] = [];
        }
        regionsPlants[regionId].push(plant);
      }
    });

    // Process region data
    Object.keys(regionsPlants).forEach((regionId) => {
      const plants = regionsPlants[regionId];
      const activeCount = plants.filter((p) => p.status === "active").length;
      const warningCount = plants.filter((p) => p.status === "warning").length;
      const errorCount = plants.filter((p) => p.status === "error").length;
      const totalCapacity = plants.reduce(
        (sum, plant) => sum + plant.capacity,
        0
      );
      const currentOutput = plants.reduce(
        (sum, plant) => sum + plant.currentOutput,
        0
      );

      this.regionData[regionId] = {
        name: this.getProvinceNameFromId(regionId),
        plantCount: plants.length,
        activeCount,
        warningCount,
        errorCount,
        offlineCount: plants.length - activeCount - warningCount - errorCount,
        totalCapacity,
        currentOutput,
      };
    });
  }

  getRegionPlants(regionId) {
    // Find all plants in this region
    return this.map.plants.filter((plant) => {
      const plantRegionId = this.findRegionForCoordinates(
        plant.latitude,
        plant.longitude
      );
      return plantRegionId === regionId;
    });
  }

  calculateRegionCapacity(regionId) {
    const plants = this.getRegionPlants(regionId);
    return plants.reduce((total, plant) => total + plant.capacity, 0);
  }

  findRegionForCoordinates(latitude, longitude) {
    // This is a simplified approach - in a real implementation,
    // you would use point-in-polygon testing to determine which region
    // contains the coordinates

    // For now, we'll use a simple proximity check to the nearest province center
    const provinceCoords = this.getProvinceCenters();

    let closestRegion = null;
    let minDistance = Infinity;

    Object.keys(provinceCoords).forEach((regionId) => {
      const region = provinceCoords[regionId];
      const distance = this.calculateDistance(
        latitude,
        longitude,
        region.latitude,
        region.longitude
      );

      if (distance < minDistance) {
        minDistance = distance;
        closestRegion = regionId;
      }
    });

    return closestRegion;
  }

  calculateDistance(lat1, lon1, lat2, lon2) {
    // Simple Euclidean distance (not accurate for geographic coords but sufficient for relative comparison)
    return Math.sqrt(Math.pow(lat1 - lat2, 2) + Math.pow(lon1 - lon2, 2));
  }

  getProvinceNameFromId(regionId) {
    // Map of region IDs to province names
    const provinceNames = {
      "TH-10": "Bangkok",
      "TH-11": "Samut Prakan",
      "TH-12": "Nonthaburi",
      "TH-13": "Pathum Thani",
      "TH-14": "Phra Nakhon Si Ayutthaya",
      "TH-15": "Ang Thong",
      "TH-16": "Lop Buri",
      "TH-17": "Sing Buri",
      "TH-18": "Chai Nat",
      "TH-19": "Saraburi",
      "TH-20": "Chon Buri",
      "TH-21": "Rayong",
      "TH-22": "Chanthaburi",
      "TH-23": "Trat",
      "TH-24": "Chachoengsao",
      "TH-25": "Prachin Buri",
      "TH-26": "Nakhon Nayok",
      "TH-27": "Sa Kaeo",
      "TH-30": "Nakhon Ratchasima",
      "TH-31": "Buriram",
      "TH-32": "Surin",
      "TH-33": "Si Sa Ket",
      "TH-34": "Ubon Ratchathani",
      "TH-35": "Yasothon",
      "TH-36": "Chaiyaphum",
      "TH-37": "Amnat Charoen",
      "TH-38": "Bueng Kan",
      "TH-39": "Nong Bua Lamphu",
      "TH-40": "Khon Kaen",
      "TH-41": "Udon Thani",
      "TH-42": "Loei",
      "TH-43": "Nong Khai",
      "TH-44": "Maha Sarakham",
      "TH-45": "Roi Et",
      "TH-46": "Kalasin",
      "TH-47": "Sakon Nakhon",
      "TH-48": "Nakhon Phanom",
      "TH-49": "Mukdahan",
      "TH-50": "Chiang Mai",
      "TH-51": "Lamphun",
      "TH-52": "Lampang",
      "TH-53": "Uttaradit",
      "TH-54": "Phrae",
      "TH-55": "Nan",
      "TH-56": "Phayao",
      "TH-57": "Chiang Rai",
      "TH-58": "Mae Hong Son",
      "TH-60": "Nakhon Sawan",
      "TH-61": "Uthai Thani",
      "TH-62": "Kamphaeng Phet",
      "TH-63": "Tak",
      "TH-64": "Sukhothai",
      "TH-65": "Phitsanulok",
      "TH-66": "Phichit",
      "TH-67": "Phetchabun",
      "TH-70": "Ratchaburi",
      "TH-71": "Kanchanaburi",
      "TH-72": "Suphan Buri",
      "TH-73": "Nakhon Pathom",
      "TH-74": "Samut Sakhon",
      "TH-75": "Samut Songkhram",
      "TH-76": "Phetchaburi",
      "TH-77": "Prachuap Khiri Khan",
      "TH-80": "Nakhon Si Thammarat",
      "TH-81": "Krabi",
      "TH-82": "Phang Nga",
      "TH-83": "Phuket",
      "TH-84": "Surat Thani",
      "TH-85": "Ranong",
      "TH-86": "Chumphon",
      "TH-90": "Songkhla",
      "TH-91": "Satun",
      "TH-92": "Trang",
      "TH-93": "Phatthalung",
      "TH-94": "Pattani",
      "TH-95": "Yala",
      "TH-96": "Narathiwat",
    };

    return provinceNames[regionId] || "Unknown Province";
  }

  getProvinceCenters() {
    // Approximate latitude/longitude for province centers
    // This would be better stored in a data file
    return {
      "TH-10": { latitude: 13.7563, longitude: 100.5018 }, // Bangkok
      "TH-50": { latitude: 18.7883, longitude: 98.9853 }, // Chiang Mai
      "TH-83": { latitude: 7.9519, longitude: 98.3381 }, // Phuket
      "TH-20": { latitude: 12.9236, longitude: 100.8824 }, // Chon Buri (Pattaya)
      "TH-40": { latitude: 16.4331, longitude: 102.8236 }, // Khon Kaen
      "TH-41": { latitude: 17.364, longitude: 102.822 }, // Udon Thani
      "TH-90": { latitude: 7.0086, longitude: 100.4747 }, // Songkhla (Hat Yai)
      "TH-14": { latitude: 14.3692, longitude: 100.5876 }, // Ayutthaya
      // Add more province centers as needed
    };
  }

  // Public methods to interact with the enhancer
  highlightRegion(regionId) {
    const region = this.map.mapGroup.querySelector(`#${regionId}`);
    if (region) {
      region.classList.add(this.options.activeClass);

      // Dispatch custom event
      const customEvent = new CustomEvent("region-highlight", {
        detail: {
          regionId,
          regionElement: region,
          regionData: this.regionData[regionId] || {},
        },
      });
      document.dispatchEvent(customEvent);

      return true;
    }
    return false;
  }

  clearHighlights() {
    const highlightedRegions = this.map.mapGroup.querySelectorAll(
      `.${this.options.hoverClass}, .${this.options.activeClass}`
    );
    highlightedRegions.forEach((region) => {
      region.classList.remove(this.options.hoverClass);
      region.classList.remove(this.options.activeClass);
    });

    this.hideRegionTooltip();
  }

  getRegionStats(regionId) {
    return this.regionData[regionId] || null;
  }

  getAllRegionStats() {
    return { ...this.regionData };
  }
}

// Initialize when the DOM is loaded and map is available
document.addEventListener("DOMContentLoaded", () => {
  // Wait for the solarMap to be initialized
  const waitForMap = setInterval(() => {
    if (window.solarMap) {
      clearInterval(waitForMap);

      // Create the hover enhancer
      const hoverEnhancer = new ThailandMapHoverEnhancer(window.solarMap, {
        enableHoverAnimation: true,
        enableProvinceStats: true,
      });

      // Make it available globally if needed
      window.mapHoverEnhancer = hoverEnhancer;

      // Listen for region selection events to update UI
      document.addEventListener("region-selected", (event) => {
        const regionData = event.detail;

        // Example: Update region stats display if it exists
        const statsElement = document.getElementById("region-stats");
        if (statsElement && regionData.isActive) {
          statsElement.innerHTML = `
            <h3>${regionData.regionData.name}</h3>
            <p>Solar Plants: ${regionData.regionData.plantCount}</p>
            <p>Total Capacity: ${
              regionData.regionData.totalCapacity?.toFixed(1) || 0
            } kW</p>
          `;
          statsElement.style.display = "block";
        } else if (statsElement) {
          statsElement.style.display = "none";
        }
      });
    }
  }, 100);
});
