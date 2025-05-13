/**
 * Weather Integration for Solar Plants Map
 * Provides weather data visualization for the map view
 */

document.addEventListener("DOMContentLoaded", function () {
  // Weather display elements
  const tempValueEl = document.getElementById("temp-value");
  const solarValueEl = document.getElementById("solar-value");

  // Current map center (default to Bangkok)
  let currentMapCenter = {
    lat: 13.7563,
    lng: 100.5018,
  };

  // Initialize the weather data
  initWeather();

  /**
   * Initialize weather data
   */
  function initWeather() {
    // Update weather on initial load
    updateWeatherData(currentMapCenter.lat, currentMapCenter.lng);

    // Listen for map center changes to update weather
    // This would integrate with your existing map implementation
    listenForMapChanges();

    // Update weather every 15 minutes
    setInterval(() => {
      updateWeatherData(currentMapCenter.lat, currentMapCenter.lng);
    }, 15 * 60 * 1000);
  }

  /**
   * Listen for map center changes
   */
  function listenForMapChanges() {
    // Check if Leaflet map is available
    if (window.leafletMap) {
      window.leafletMap.on("moveend", function () {
        const center = window.leafletMap.getCenter();
        currentMapCenter = {
          lat: center.lat,
          lng: center.lng,
        };
        updateWeatherData(currentMapCenter.lat, currentMapCenter.lng);
      });
    }

    // Also listen for custom events from your Thailand SVG map
    document.addEventListener("map-center-changed", function (event) {
      if (event.detail && event.detail.lat && event.detail.lng) {
        currentMapCenter = {
          lat: event.detail.lat,
          lng: event.detail.lng,
        };
        updateWeatherData(currentMapCenter.lat, currentMapCenter.lng);
      }
    });
  }

  /**
   * Update weather data for given coordinates
   */
  function updateWeatherData(lat, lng) {
    // In a real implementation, you would fetch from a weather API
    // For this example, we'll use simulated data

    // Show loading state
    if (tempValueEl)
      tempValueEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    if (solarValueEl)
      solarValueEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    // Simulate API call delay
    setTimeout(() => {
      // Generate simulated weather data
      const simulatedData = getSimulatedWeatherData(lat, lng);

      // Update UI
      if (tempValueEl)
        tempValueEl.textContent = `${simulatedData.temperature}°C`;
      if (solarValueEl)
        solarValueEl.textContent = `${simulatedData.solarIrradiance} W/m²`;

      // Update weather icon based on conditions
      updateWeatherIcon(simulatedData.conditions);

      // In a real implementation, you might add a small indicator to show data freshness
      const weatherContainer = document.querySelector(
        ".absolute.top-4.right-4"
      );
      if (weatherContainer) {
        const timestamp = document.createElement("div");
        timestamp.className = "text-xs text-gray-500 text-center mt-1";
        timestamp.textContent = "Updated: " + getCurrentTime();

        // Remove any existing timestamp
        const existingTimestamp = weatherContainer.querySelector(
          ".text-xs.text-gray-500"
        );
        if (existingTimestamp) {
          existingTimestamp.remove();
        }

        weatherContainer.appendChild(timestamp);
      }
    }, 700); // Simulate delay of 700ms
  }

  /**
   * Update weather icon based on conditions
   */
  function updateWeatherIcon(conditions) {
    const iconContainer = document.querySelector(".absolute.top-4.right-4");

    if (!iconContainer) return;

    // Check if weather icon already exists
    let weatherIcon = iconContainer.querySelector(".weather-icon");
    if (!weatherIcon) {
      // Create weather icon element
      weatherIcon = document.createElement("div");
      weatherIcon.className =
        "weather-icon absolute -top-3 -right-3 w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center";
      iconContainer.appendChild(weatherIcon);
    }

    // Set icon based on conditions
    switch (conditions) {
      case "sunny":
        weatherIcon.innerHTML = '<i class="fas fa-sun text-yellow-500"></i>';
        break;
      case "partly-cloudy":
        weatherIcon.innerHTML =
          '<i class="fas fa-cloud-sun text-gray-400"></i>';
        break;
      case "cloudy":
        weatherIcon.innerHTML = '<i class="fas fa-cloud text-gray-400"></i>';
        break;
      case "rainy":
        weatherIcon.innerHTML =
          '<i class="fas fa-cloud-rain text-blue-400"></i>';
        break;
      default:
        weatherIcon.innerHTML = '<i class="fas fa-sun text-yellow-500"></i>';
    }
  }

  /**
   * Get simulated weather data based on coordinates
   */
  function getSimulatedWeatherData(lat, lng) {
    // In a real app, this would be an API call to a weather service

    // Use coordinates to generate deterministic but realistic values
    const dateHash = new Date().getDate() + new Date().getMonth() * 30;
    const locationHash = Math.floor((lat * 10 + lng) * 100) % 100;
    const combinedHash = (dateHash + locationHash) % 100;

    // Temperature between 25-38°C, typical for Thailand
    const temperature = 25 + (combinedHash % 13);

    // Solar irradiance between 300-950 W/m²
    const baseIrradiance = 300 + combinedHash * 6.5;

    // Adjust for time of day (simplified)
    const hour = new Date().getHours();
    let timeMultiplier = 0.1; // Default for night

    if (hour >= 6 && hour < 18) {
      // Daytime: peak at noon
      const hoursFromNoon = Math.abs(12 - hour);
      timeMultiplier = 1 - hoursFromNoon / 12;
    }

    const solarIrradiance = Math.round(baseIrradiance * timeMultiplier);

    // Determine weather conditions
    let conditions;
    if (combinedHash < 60) {
      conditions = "sunny";
    } else if (combinedHash < 80) {
      conditions = "partly-cloudy";
    } else if (combinedHash < 95) {
      conditions = "cloudy";
    } else {
      conditions = "rainy";
    }

    return {
      temperature,
      solarIrradiance,
      conditions,
    };
  }

  /**
   * Get formatted current time
   */
  function getCurrentTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    return `${hours}:${minutes}`;
  }
});
