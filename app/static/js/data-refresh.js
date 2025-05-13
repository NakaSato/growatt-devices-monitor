/**
 * Data Refresh Functionality - Auto-refresh plant data
 * Provides automatic and manual refresh functionality for plant data
 */

document.addEventListener("DOMContentLoaded", function () {
  // Refresh control elements
  let refreshButton;
  let autoRefreshToggle;
  let lastRefreshIndicator;

  // Refresh settings
  let autoRefreshEnabled = false;
  let refreshInterval = 5 * 60 * 1000; // 5 minutes
  let refreshTimer = null;
  let lastRefreshTime = new Date();

  // Initialize refresh functionality
  initRefreshControls();

  /**
   * Initialize refresh controls
   */
  function initRefreshControls() {
    // Create refresh button if it doesn't exist
    if (!document.getElementById("data-refresh-btn")) {
      // Create refresh container
      const refreshContainer = document.createElement("div");
      refreshContainer.className =
        "absolute bottom-20 right-5 z-10 flex flex-col space-y-2";

      // Create refresh button
      refreshButton = document.createElement("button");
      refreshButton.id = "data-refresh-btn";
      refreshButton.className =
        "w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center text-blue-600 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
      refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
      refreshButton.setAttribute("title", "Refresh data");
      refreshButton.addEventListener("click", manualRefresh);

      // Create auto refresh toggle
      autoRefreshToggle = document.createElement("button");
      autoRefreshToggle.id = "auto-refresh-toggle";
      autoRefreshToggle.className =
        "w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center text-gray-600 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
      autoRefreshToggle.innerHTML = '<i class="fas fa-clock"></i>';
      autoRefreshToggle.setAttribute(
        "title",
        "Toggle auto-refresh (currently OFF)"
      );
      autoRefreshToggle.addEventListener("click", toggleAutoRefresh);

      // Add buttons to container
      refreshContainer.appendChild(refreshButton);
      refreshContainer.appendChild(autoRefreshToggle);

      // Add to page - best to add near the map controls
      const mapControlsContainer = document.querySelector(
        ".absolute.bottom-5.right-5"
      );
      if (mapControlsContainer && mapControlsContainer.parentNode) {
        mapControlsContainer.parentNode.appendChild(refreshContainer);
      } else {
        // Fallback if map controls container not found
        const mapContainer = document.querySelector(".lg\\:col-span-3");
        if (mapContainer) {
          mapContainer.appendChild(refreshContainer);
        }
      }

      // Create last refresh indicator
      lastRefreshIndicator = document.createElement("div");
      lastRefreshIndicator.id = "last-refresh-indicator";
      lastRefreshIndicator.className =
        "absolute bottom-4 left-1/2 transform -translate-x-1/2 text-xs text-gray-500 bg-white/80 py-1 px-2 rounded-full shadow-sm z-10";
      lastRefreshIndicator.textContent = "Last updated: just now";

      const mapContainer = document.querySelector(".lg\\:col-span-3");
      if (mapContainer) {
        mapContainer.appendChild(lastRefreshIndicator);
      }
    } else {
      // Get existing elements
      refreshButton = document.getElementById("data-refresh-btn");
      autoRefreshToggle = document.getElementById("auto-refresh-toggle");
      lastRefreshIndicator = document.getElementById("last-refresh-indicator");
    }

    // Start checking last refresh time
    updateLastRefreshTime();
    setInterval(updateLastRefreshTime, 60000); // Update every minute
  }

  /**
   * Manual refresh handler
   */
  function manualRefresh() {
    // Show loading state
    setRefreshLoading(true);

    // In a real application, this would call a server endpoint or refetch data
    // For this demo, we'll simulate a refresh with a timeout
    setTimeout(() => {
      // Update the data
      refreshData();

      // Update last refresh time
      lastRefreshTime = new Date();
      updateLastRefreshTime();

      // Reset loading state
      setRefreshLoading(false);

      // Show success notification
      showNotification("Data refreshed successfully", "success");
    }, 1500);
  }

  /**
   * Toggle auto-refresh functionality
   */
  function toggleAutoRefresh() {
    autoRefreshEnabled = !autoRefreshEnabled;

    if (autoRefreshEnabled) {
      // Enable auto-refresh
      autoRefreshToggle.className = autoRefreshToggle.className.replace(
        "text-gray-600",
        "text-green-600"
      );
      autoRefreshToggle.setAttribute(
        "title",
        "Toggle auto-refresh (currently ON)"
      );

      // Start refresh timer
      refreshTimer = setInterval(() => {
        manualRefresh();
      }, refreshInterval);

      showNotification("Auto-refresh enabled (every 5 minutes)", "info");
    } else {
      // Disable auto-refresh
      autoRefreshToggle.className = autoRefreshToggle.className.replace(
        "text-green-600",
        "text-gray-600"
      );
      autoRefreshToggle.setAttribute(
        "title",
        "Toggle auto-refresh (currently OFF)"
      );

      // Clear refresh timer
      if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
      }

      showNotification("Auto-refresh disabled", "info");
    }
  }

  /**
   * Set refresh button loading state
   */
  function setRefreshLoading(isLoading) {
    if (!refreshButton) return;

    if (isLoading) {
      refreshButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      refreshButton.disabled = true;
    } else {
      refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
      refreshButton.disabled = false;
    }
  }

  /**
   * Update the last refresh time indicator
   */
  function updateLastRefreshTime() {
    if (!lastRefreshIndicator) return;

    const now = new Date();
    const diffMs = now - lastRefreshTime;
    const diffMins = Math.floor(diffMs / 60000);

    let timeText;
    if (diffMins < 1) {
      timeText = "just now";
    } else if (diffMins === 1) {
      timeText = "1 minute ago";
    } else if (diffMins < 60) {
      timeText = `${diffMins} minutes ago`;
    } else {
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours === 1) {
        timeText = "1 hour ago";
      } else {
        timeText = `${diffHours} hours ago`;
      }
    }

    lastRefreshIndicator.textContent = `Last updated: ${timeText}`;

    // Add warning class if data is getting stale (> 15 minutes)
    if (diffMins > 15) {
      lastRefreshIndicator.classList.add("bg-yellow-100", "text-yellow-700");
    } else {
      lastRefreshIndicator.classList.remove("bg-yellow-100", "text-yellow-700");
    }
  }

  /**
   * Refresh data and update UI
   */
  function refreshData() {
    // In a real application, this would fetch fresh data from the server
    // For this demo, we'll just simulate a data update by modifying existing data

    if (window.solarPlantsData && window.solarPlantsData.length > 0) {
      // Clone original data to avoid mutating the original
      const refreshedData = JSON.parse(JSON.stringify(window.solarPlantsData));

      // Update each plant with slightly different values
      refreshedData.forEach((plant) => {
        // Create random fluctuations in output
        const outputMultiplier = 0.8 + Math.random() * 0.4; // 0.8 to 1.2
        plant.currentOutput = parseFloat(
          (plant.currentOutput * outputMultiplier).toFixed(1)
        );

        // Increase today's energy based on time of day
        const hour = new Date().getHours();
        if (hour >= 6 && hour < 19) {
          // Daytime hours
          const energyIncrease = Math.random() * 5 + 2; // 2-7 kWh increase
          plant.todayEnergy = parseFloat(
            (plant.todayEnergy + energyIncrease).toFixed(1)
          );
        }

        // Occasionally change plant status
        const statusRoll = Math.random() * 100;
        if (statusRoll < 2) {
          // 2% chance
          // Get current status index
          const statuses = ["active", "warning", "error", "offline"];
          const currentIndex = statuses.indexOf(plant.status);

          // Pick a new random status
          let newIndex;
          do {
            newIndex = Math.floor(Math.random() * statuses.length);
          } while (newIndex === currentIndex);

          plant.status = statuses[newIndex];
        }
      });

      // Update the global data
      window.solarPlantsData = refreshedData;

      // Trigger update in relevant components
      if (typeof window.updateMapDisplay === "function") {
        window.updateMapDisplay(refreshedData);
      }

      // Update specific plant if one is selected
      if (window.Alpine) {
        document.querySelectorAll("[x-data]").forEach((element) => {
          const data = window.Alpine.$data(element);
          if (data.hasOwnProperty("selectedPlant") && data.selectedPlant) {
            // Find the refreshed plant data
            const updatedPlant = refreshedData.find(
              (p) => p.id === data.selectedPlant.id
            );
            if (updatedPlant) {
              data.selectedPlant = updatedPlant;
            }
          }
        });
      }
    }
  }

  /**
   * Show notification
   */
  function showNotification(message, type = "info") {
    // Create notification element if it doesn't exist
    let notification = document.getElementById("refresh-notification");
    if (!notification) {
      notification = document.createElement("div");
      notification.id = "refresh-notification";
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
