/**
 * Plant detail utilities for handling plant detail information
 */

// Sample plant data for fallback when API or backend fails
const samplePlantData = [
  {
    id: 10125058,
    name: "Sample Plant 1",
    plantName: "Sample Plant 1",
    status: "active",
    currentPower: 15.5,
    eToday: 75.2,
    eMonth: 1250.5,
    eTotal: 42500.8,
    capacity: 20.0,
    nominalPower: 20000,
    latitude: 37.7749,
    longitude: -122.4194,
    lat: 37.7749,
    lng: -122.4194,
    city: "San Francisco",
    country: "USA",
    creatDate: "2023-01-15T08:30:00Z",
    lastUpdateTime: new Date().toISOString(),
    co2: 21250.4,
    coal: 8500.2,
    tree: 350,
    plantType: "Commercial",
    timezone: "8",
    moneyUnit: "USD",
    moneyUnitText: "US Dollar",
    isShare: false,
    onlineNum: 4,
    accountName: "demo_account",
    designCompany: "Solar Solutions Inc."
  },
  {
    id: 10125059,
    name: "Sample Plant 2",
    plantName: "Sample Plant 2",
    status: "warning",
    currentPower: 8.2,
    eToday: 45.6,
    eMonth: 950.3,
    eTotal: 25800.5,
    capacity: 12.5,
    nominalPower: 12500,
    latitude: 34.0522,
    longitude: -118.2437,
    lat: 34.0522,
    lng: -118.2437,
    city: "Los Angeles",
    country: "USA",
    creatDate: "2023-03-22T10:15:00Z",
    lastUpdateTime: new Date().toISOString(),
    co2: 12900.1,
    coal: 5160.0,
    tree: 215,
    plantType: "Residential",
    timezone: "8",
    moneyUnit: "USD",
    moneyUnitText: "US Dollar",
    isShare: true,
    onlineNum: 2,
    accountName: "demo_account",
    designCompany: "GreenTech Solar"
  }
];

/**
 * Initialize sample plant data if not available
 * Ensures sample data is available for fallback
 */
function initializeSamplePlants() {
  if (typeof window.sample_plants === 'undefined') {
    window.sample_plants = samplePlantData;
  }
}

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

// Calculate total pages for details pagination
function calculateDetailsTotalPages(details, perPage) {
  if (!details) return 1;
  return Math.ceil(Object.keys(details).length / perPage);
}

// Initialize sample data when script loads
initializeSamplePlants();

// Expose functions to global scope
window.PlantDetailUtils = {
  formatDate,
  formatEnergy,
  formatPower,
  formatKeyName,
  formatPlantValue,
  fetchPlantDetails,
  fetchPlantsList,
  normalizeAPIResponse,
  getPlantStatus,
  paginatePlantDetails,
  calculateDetailsTotalPages,
  initializeSamplePlants
};
