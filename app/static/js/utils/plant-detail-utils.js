/**
 * Plant detail utilities for handling plant detail information
 */

/**
 * Format date for display in plant details
 * @param {string} dateString - Date string from API
 * @returns {string} Formatted date string
 */
function formatDate(dateString) {
  if (!dateString) return "N/A";

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format energy values with appropriate precision
 * @param {number} value - Energy value
 * @returns {string} Formatted energy value
 */
function formatEnergy(value) {
  if (value === undefined || value === null) return "N/A";
  return Number(value).toFixed(2);
}

/**
 * Format power values with appropriate precision
 * @param {number} value - Power value
 * @returns {string} Formatted power value
 */
function formatPower(value) {
  if (value === undefined || value === null) return "N/A";
  return Number(value).toFixed(2);
}

/**
 * Format key names to be more readable
 * @param {string} key - Object key name
 * @returns {string} Formatted key name
 */
function formatKeyName(key) {
  if (!key) return "";

  // Convert camelCase to Title Case with spaces
  return key
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, function (str) {
      return str.toUpperCase();
    })
    .trim();
}

/**
 * Format plant values based on key type
 * @param {string} key - Object key
 * @param {any} value - Value to format
 * @returns {string} Formatted value
 */
function formatPlantValue(key, value) {
  if (value === undefined || value === null) return "N/A";

  // Format based on key name patterns
  if (key.includes("date") || key.includes("Date")) {
    return formatDate(value);
  } else if (key.includes("power") || key.includes("Power")) {
    return formatPower(value) + " kW";
  } else if (
    key.includes("energy") ||
    key.includes("Energy") ||
    key.includes("eToday") ||
    key.includes("eMonth") ||
    key.includes("eTotal")
  ) {
    return formatEnergy(value) + " kWh";
  } else if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  } else if (typeof value === "number") {
    return value.toString();
  } else if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return value.toString();
}

/**
 * Utility functions for handling plant details
 */

function fetchPlantDetails(plantId) {
  return fetch(`/api/plants/${plantId}/details`).then((response) => {
    if (!response.ok) {
      throw new Error("Failed to fetch plant details");
    }
    return response.json();
  });
}

/**
 * Fetch plants list from the API
 * @param {Object} options - Fetch options like pagination parameters
 * @returns {Promise} Promise resolving to plants data
 */
function fetchPlantsList(options = {}) {
  const { page = 1, pageSize = 20 } = options;

  return fetch(`/api/plants?page=${page}&pageSize=${pageSize}`, {
    headers: {
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      // Log the received data to console for debugging
      console.log("Received plants data:", data);

      return normalizeAPIResponse(data);
    });
}

/**
 * Normalize API response to a consistent format
 * @param {Object} response - Raw API response
 * @returns {Object} Normalized response with consistent property names
 */
function normalizeAPIResponse(response) {
  let result = {
    currentPage: 1,
    totalPages: 1,
    pageSize: 20,
    totalCount: 0,
    plants: [],
  };

  try {
    // Handle different API response formats
    if (response.currPage !== undefined) {
      // Format matches the example response
      result.currentPage = response.currPage;
      result.totalPages = response.pages;
      result.pageSize = response.pageSize;
      result.totalCount = response.count;

      // Map plant data to a consistent format
      if (Array.isArray(response.datas)) {
        result.plants = response.datas.map((plant) => ({
          id: plant.id,
          plantName: plant.plantName || plant.name || `Plant ${plant.id}`,
          status: getPlantStatus(plant),
          totalPower: parseFloat(plant.currentPac || 0),
          todayEnergy: parseFloat(plant.eToday || 0),
          plantType: plant.plantType,
          accountName: plant.accountName,
          plantImg: plant.plantImg,
          onlineNum: parseInt(plant.onlineNum || 0, 10),
          // Add additional normalized properties as needed
          formattedLastUpdate: formatDate(plant.lastUpdateTime),
        }));
      }
    } else if (Array.isArray(response)) {
      // Handle case where response is an array of plants
      result.plants = response.map((plant) => ({
        id: plant.id,
        plantName: plant.plantName || plant.name || `Plant ${plant.id}`,
        status: getPlantStatus(plant),
        totalPower: parseFloat(
          plant.currentPac || plant.totalPower || plant.current_power || 0
        ),
        todayEnergy: parseFloat(
          plant.eToday || plant.todayEnergy || plant.today_energy || 0
        ),
        // Add additional normalized properties as needed
        formattedLastUpdate: formatDate(
          plant.lastUpdateTime || plant.last_update_time
        ),
      }));
      result.totalCount = response.length;
    } else if (response.plants && Array.isArray(response.plants)) {
      // Handle case where response has a plants property
      result = {
        ...result,
        ...response,
        plants: response.plants.map((plant) => ({
          id: plant.id,
          plantName: plant.plantName || plant.name || `Plant ${plant.id}`,
          status: getPlantStatus(plant),
          totalPower: parseFloat(
            plant.currentPac || plant.totalPower || plant.current_power || 0
          ),
          todayEnergy: parseFloat(
            plant.eToday || plant.todayEnergy || plant.today_energy || 0
          ),
          // Add additional normalized properties as needed
          formattedLastUpdate: formatDate(
            plant.lastUpdateTime || plant.last_update_time
          ),
        })),
      };
    }
  } catch (error) {
    console.error("Error normalizing API response:", error);
  }

  return result;
}

/**
 * Determine plant status based on available data
 * @param {Object} plant - Plant data
 * @returns {string} Plant status (active, inactive, maintenance, error)
 */
function getPlantStatus(plant) {
  // If status is explicitly provided, use it
  if (plant.status) return plant.status;

  // Determine status based on online devices
  if (plant.onlineNum && parseInt(plant.onlineNum, 10) > 0) {
    return "active";
  }

  // Determine status based on power output
  if (plant.currentPac && parseFloat(plant.currentPac) > 0) {
    return "active";
  }

  // Default to inactive if no other information is available
  return "inactive";
}

// Paginate plant details object
function paginatePlantDetails(details, page, perPage) {
  if (!details) return {};

  const keys = Object.keys(details);
  const startIndex = (page - 1) * perPage;
  const endIndex = startIndex + perPage;
  const paginatedKeys = keys.slice(startIndex, endIndex);

  const result = {};
  paginatedKeys.forEach((key) => {
    result[key] = details[key];
  });

  return result;
}

// Calculate total pages for plant details
function calculateDetailsTotalPages(details, perPage) {
  if (!details) return 1;
  const totalItems = Object.keys(details).length;
  return Math.ceil(totalItems / perPage);
}
