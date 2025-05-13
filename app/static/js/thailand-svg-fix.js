/**
 * Thailand SVG Map Fix
 * This script fixes issues with SVG map interactivity
 */

document.addEventListener("DOMContentLoaded", function () {
  // Fix function to be called when Thailand map is shown
  function fixThailandSvgMap() {
    console.log("Applying Thailand SVG Map fix...");

    // Get the SVG element
    const svgElement = document.getElementById("thailand-svg");
    if (!svgElement) {
      console.error("Thailand SVG element not found");
      return;
    }

    // Make sure SVG has appropriate dimensions and styles
    svgElement.style.width = "100%";
    svgElement.style.height = "100%";
    svgElement.style.pointerEvents = "auto";

    // Fix pointer events on all regions
    const regions = document.querySelectorAll(".region");
    regions.forEach((region) => {
      // Ensure the path is clickable
      region.style.pointerEvents = "auto";
      region.style.cursor = "pointer";

      // Remove and re-add click event listeners to ensure they work
      const regionId = region.getAttribute("data-region-id");
      const regionName = region.getAttribute("data-region-name");

      // Remove existing listeners by cloning the node
      const oldRegion = region;
      const newRegion = oldRegion.cloneNode(true);
      if (oldRegion.parentNode) {
        oldRegion.parentNode.replaceChild(newRegion, oldRegion);
      }

      // Add click event listener
      newRegion.addEventListener("click", function (e) {
        e.stopPropagation(); // Stop event bubbling
        console.log(`Region clicked: ${regionName}`);

        // Highlight the clicked region
        regions.forEach((r) => r.setAttribute("fill", "#e6f4ff"));
        this.setAttribute("fill", "#b0d0ff");

        // Create region data
        const regionData = {
          name: regionName,
          plants: getRegionPlants(regionId),
        };

        // Dispatch custom event
        const event = new CustomEvent("region-selected", {
          detail: {
            regionId,
            regionData,
            isActive: true,
            plants: getRegionPlants(regionId),
          },
        });

        document.dispatchEvent(event);
      });

      // Add hover effects
      newRegion.addEventListener("mouseenter", function () {
        if (this.getAttribute("fill") !== "#b0d0ff") {
          this.setAttribute("fill", "url(#region-gradient)");
        }
        this.setAttribute("stroke-width", "3");
      });

      newRegion.addEventListener("mouseleave", function () {
        if (this.getAttribute("fill") !== "#b0d0ff") {
          this.setAttribute("fill", "#e6f4ff");
        }
        this.setAttribute("stroke-width", "2");
      });
    });

    // Fix the map container
    const mapContainer = document.getElementById("thailand-map-container");
    if (mapContainer) {
      mapContainer.style.pointerEvents = "auto";
    }

    // Add event listener to SVG element for debugging
    svgElement.addEventListener("click", function (e) {
      console.log("SVG clicked at:", e.clientX, e.clientY);
    });

    console.log("Thailand SVG Map fix applied successfully");
  }

  // Helper function to get plants for a region
  function getRegionPlants(regionId) {
    // Filter the global plants data by region
    return (window.plantsData || []).filter(
      (plant) =>
        plant.region && plant.region.toLowerCase() === regionId.toLowerCase()
    );
  }

  // Fix the map when the tab or button is clicked
  const thailandTab = document.getElementById("thailand-tab");
  if (thailandTab) {
    thailandTab.addEventListener("click", function () {
      // Wait for the DOM to update
      setTimeout(fixThailandSvgMap, 200);
    });
  }

  const svgMapBtn = document.getElementById("svg-map-btn");
  if (svgMapBtn) {
    svgMapBtn.addEventListener("click", function () {
      // Wait for the DOM to update
      setTimeout(fixThailandSvgMap, 200);
    });
  }

  // Also fix the map on initial load if it's visible
  const thailandMapContainer = document.getElementById(
    "thailand-map-container"
  );
  if (
    thailandMapContainer &&
    !thailandMapContainer.classList.contains("hidden")
  ) {
    setTimeout(fixThailandSvgMap, 500);
  }
});
