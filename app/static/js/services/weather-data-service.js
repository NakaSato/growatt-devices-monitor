/**
 * Weather Data Service
 * Handles fetching, caching, and processing weather data
 */
window.WeatherDataService = (function () {
  const cacheExpiration = 15 * 60 * 1000; // Cache expiration time in milliseconds (15 minutes)
  let plantId = null;
  let cacheKey = null;

  return {
    /**
     * Initialize the service with a plant ID
     * @param {string} id - The plant ID
     */
    init: function (id) {
      plantId = id;
      cacheKey = `weather_${plantId}`;
      console.log(`Weather Data Service initialized for plant ID: ${plantId}`);
    },

    /**
     * Retrieve cached weather data if valid
     * @returns {Array|null} The cached data or null if invalid/missing
     */
    getCachedData: function () {
      const cachedData = localStorage.getItem(cacheKey);

      if (cachedData) {
        try {
          const parsedCache = JSON.parse(cachedData);
          const isCacheValid =
            Date.now() - parsedCache.timestamp < cacheExpiration;

          if (isCacheValid) {
            console.log("Using cached weather data");
            return parsedCache.data;
          }
        } catch (error) {
          console.error("Error parsing cache:", error);
          // Clear invalid cache
          localStorage.removeItem(cacheKey);
        }
      }

      return null;
    },

    /**
     * Fetch weather data from the API
     * @returns {Promise<Array>} Promise resolving to weather data array
     */
    fetchWeatherData: function () {
      console.log(`Fetching weather data for plant ID: ${plantId}`);

      return fetch(`/api/weather?plantId=${plantId}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          const weatherData = Array.isArray(data) ? data : [];

          // Cache the data with timestamp
          this.cacheData(weatherData);

          return weatherData;
        });
    },

    /**
     * Cache weather data with current timestamp
     * @param {Array} data - The weather data to cache
     */
    cacheData: function (data) {
      const cacheData = {
        timestamp: Date.now(),
        data: data,
      };

      try {
        localStorage.setItem(cacheKey, JSON.stringify(cacheData));
        console.log("Weather data cached successfully");
      } catch (error) {
        console.error("Error caching weather data:", error);
      }
    },

    /**
     * Clear cached weather data
     */
    clearCache: function () {
      localStorage.removeItem(cacheKey);
      console.log("Weather data cache cleared");
    },
  };
})();
