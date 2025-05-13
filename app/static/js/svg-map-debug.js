// Add SVG map debug script
document.addEventListener("DOMContentLoaded", function () {
  console.log("SVG Map Debug Script loaded");

  // Debug function to log SVG click events
  function addSVGDebugListeners() {
    const svgElement = document.getElementById("thailand-svg");
    if (!svgElement) {
      console.log("SVG element not found");
      return;
    }

    console.log("Adding debug listeners to SVG");

    // Add click listener to the SVG element
    svgElement.addEventListener("click", function (e) {
      console.log("SVG clicked at:", e.clientX, e.clientY);
    });

    // Add listeners to all regions
    const regions = document.querySelectorAll(".region");
    console.log("Found", regions.length, "regions");

    regions.forEach((region, index) => {
      // Add specific debug click handler
      region.addEventListener("click", function (e) {
        e.stopPropagation(); // Prevent event from bubbling up
        const regionId = this.getAttribute("data-region-id");
        const regionName = this.getAttribute("data-region-name");
        console.log(`Region ${index} clicked:`, regionId, regionName);

        // Make the region visually respond
        this.setAttribute("fill", "#b1d8ff");
        setTimeout(() => {
          this.setAttribute("fill", "#e6f4ff");
        }, 500);

        // Force event to dispatch
        const event = new CustomEvent("region-selected", {
          detail: {
            regionId,
            regionData: {
              name: regionName,
              plants: window.plantsData
                ? window.plantsData.filter(
                    (p) =>
                      p.region &&
                      p.region.toLowerCase() === regionId.toLowerCase()
                  )
                : [],
            },
            isActive: true,
          },
        });
        document.dispatchEvent(event);
        console.log("Dispatched region-selected event for", regionId);
      });

      // Make sure the region has the right pointer properties
      region.style.pointerEvents = "all";
      region.style.cursor = "pointer";
    });

    // Add listeners to markers group
    const markersGroup = document.getElementById("map-markers");
    if (markersGroup) {
      console.log("Adding listeners to markers group");
      markersGroup.style.pointerEvents = "all";
    }
  }

  // Call this function after a slight delay to ensure all elements are loaded
  setTimeout(addSVGDebugListeners, 500);

  // Also add it when the Thailand tab is clicked
  const thailandTab = document.getElementById("thailand-tab");
  if (thailandTab) {
    thailandTab.addEventListener("click", function () {
      console.log("Thailand tab clicked, adding debug listeners");
      setTimeout(addSVGDebugListeners, 100);
    });
  }

  // Also add it when the SVG map button is clicked
  const svgMapBtn = document.getElementById("svg-map-btn");
  if (svgMapBtn) {
    svgMapBtn.addEventListener("click", function () {
      console.log("SVG map button clicked, adding debug listeners");
      setTimeout(addSVGDebugListeners, 100);
    });
  }
});
