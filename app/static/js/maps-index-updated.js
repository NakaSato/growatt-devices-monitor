/**
 * Maps Index - Solar Plants Data and Map Integration
 * This file provides data and functionality for the solar plants map component
 * Modified for Satellite map view only
 */

// Sample data for solar plants in Thailand
const solarPlantsData = [
  {
    id: "plant001",
    name: "Bangkok Solar Farm",
    status: "active",
    capacity: 50.0,
    currentOutput: 42.5,
    todayEnergy: 215.6,
    peakOutput: 48.2,
    installDate: "2021-05-15",
    location: "Bangkok",
    latitude: 13.7563,
    longitude: 100.5018,
  },
  {
    id: "plant002",
    name: "Chiang Mai Green Energy",
    status: "active",
    capacity: 35.0,
    currentOutput: 30.2,
    todayEnergy: 156.3,
    peakOutput: 33.8,
    installDate: "2021-08-22",
    location: "Chiang Mai",
    latitude: 18.7883,
    longitude: 98.9853,
  },
  {
    id: "plant003",
    name: "Phuket Solar Array",
    status: "warning",
    capacity: 25.0,
    currentOutput: 15.8,
    todayEnergy: 102.4,
    peakOutput: 22.7,
    installDate: "2022-01-10",
    location: "Phuket",
    latitude: 7.9519,
    longitude: 98.3381,
  },
  {
    id: "plant004",
    name: "Pattaya Sun Power",
    status: "error",
    capacity: 40.0,
    currentOutput: 0.0,
    todayEnergy: 45.2,
    peakOutput: 12.5,
    installDate: "2021-11-05",
    location: "Pattaya",
    latitude: 12.9236,
    longitude: 100.8824,
  },
  {
    id: "plant005",
    name: "Khon Kaen Solar Hub",
    status: "active",
    capacity: 30.0,
    currentOutput: 28.1,
    todayEnergy: 145.7,
    peakOutput: 29.4,
    installDate: "2022-03-18",
    location: "Khon Kaen",
    latitude: 16.4331,
    longitude: 102.8236,
  },
  {
    id: "plant006",
    name: "Udon Thani Solar Park",
    status: "active",
    capacity: 22.0,
    currentOutput: 19.5,
    todayEnergy: 105.8,
    peakOutput: 21.2,
    installDate: "2022-02-25",
    location: "Udon Thani",
    latitude: 17.364,
    longitude: 102.822,
  },
  {
    id: "plant007",
    name: "Hat Yai Power Plant",
    status: "offline",
    capacity: 18.0,
    currentOutput: 0.0,
    todayEnergy: 0.0,
    peakOutput: 0.0,
    installDate: "2021-12-12",
    location: "Hat Yai",
    latitude: 7.0086,
    longitude: 100.4747,
  },
  {
    id: "plant008",
    name: "Ayutthaya Solar Field",
    status: "active",
    capacity: 15.0,
    currentOutput: 13.2,
    todayEnergy: 78.4,
    peakOutput: 14.7,
    installDate: "2021-10-30",
    location: "Ayutthaya",
    latitude: 14.3692,
    longitude: 100.5876,
  },
  {
    id: "plant009",
    name: "Chonburi Energy Center",
    status: "warning",
    capacity: 28.0,
    currentOutput: 20.1,
    todayEnergy: 115.2,
    peakOutput: 26.8,
    installDate: "2022-04-05",
    location: "Chonburi",
    latitude: 13.3611,
    longitude: 100.9847,
  },
  {
    id: "plant010",
    name: "Rayong Green Power",
    status: "active",
    capacity: 45.0,
    currentOutput: 40.2,
    todayEnergy: 198.6,
    peakOutput: 43.5,
    installDate: "2021-09-15",
    location: "Rayong",
    latitude: 12.6833,
    longitude: 101.2833,
  },
];

// Generate more plants for demo purposes
function generateAdditionalPlants(baseCount) {
  const additionalPlants = [];
  const regions = [
    {
      name: "Northern Thailand",
      lat: { min: 16.5, max: 20.5 },
      lng: { min: 97.5, max: 101.0 },
    },
    {
      name: "Northeastern Thailand",
      lat: { min: 14.0, max: 18.0 },
      lng: { min: 101.5, max: 105.5 },
    },
    {
      name: "Central Thailand",
      lat: { min: 13.0, max: 16.0 },
      lng: { min: 99.0, max: 101.5 },
    },
    {
      name: "Eastern Thailand",
      lat: { min: 12.0, max: 14.0 },
      lng: { min: 101.0, max: 103.0 },
    },
    {
      name: "Western Thailand",
      lat: { min: 12.0, max: 18.0 },
      lng: { min: 98.0, max: 99.5 },
    },
    {
      name: "Southern Thailand",
      lat: { min: 6.0, max: 12.0 },
      lng: { min: 98.0, max: 102.0 },
    },
  ];

  const statuses = ["active", "warning", "error", "offline"];
  const statusWeights = [70, 15, 10, 5]; // Weighted distribution
  const capacityRanges = [
    { min: 5, max: 15, weight: 40 },
    { min: 16, max: 30, weight: 30 },
    { min: 31, max: 50, weight: 20 },
    { min: 51, max: 100, weight: 10 },
  ];

  // Create a weighted random selection function
  function weightedRandom(items, weights) {
    const cumulativeWeights = [];
    let sum = 0;

    for (let i = 0; i < weights.length; i++) {
      sum += weights[i];
      cumulativeWeights[i] = sum;
    }

    const random = Math.random() * sum;

    for (let i = 0; i < cumulativeWeights.length; i++) {
      if (random < cumulativeWeights[i]) {
        return items[i];
      }
    }

    return items[0]; // Fallback
  }

  // Generate random plants
  for (let i = 0; i < baseCount; i++) {
    const regionIndex = Math.floor(Math.random() * regions.length);
    const region = regions[regionIndex];

    // Generate random coordinates within the region
    const lat =
      region.lat.min + Math.random() * (region.lat.max - region.lat.min);
    const lng =
      region.lng.min + Math.random() * (region.lng.max - region.lng.min);

    // Select a random capacity range based on weights
    const capacityRange = weightedRandom(
      capacityRanges,
      capacityRanges.map((r) => r.weight)
    );
    const capacity =
      Math.round(
        (capacityRange.min +
          Math.random() * (capacityRange.max - capacityRange.min)) *
          10
      ) / 10;

    // Select status based on weighted distribution
    const status = weightedRandom(statuses, statusWeights);

    // Generate random output based on status
    let currentOutput = 0;
    let todayEnergy = 0;
    let peakOutput = 0;

    if (status === "active") {
      currentOutput =
        Math.round(capacity * (0.75 + Math.random() * 0.2) * 10) / 10;
      todayEnergy =
        Math.round(currentOutput * (4 + Math.random() * 3) * 10) / 10;
      peakOutput =
        Math.round(capacity * (0.85 + Math.random() * 0.15) * 10) / 10;
    } else if (status === "warning") {
      currentOutput =
        Math.round(capacity * (0.4 + Math.random() * 0.3) * 10) / 10;
      todayEnergy =
        Math.round(currentOutput * (2 + Math.random() * 3) * 10) / 10;
      peakOutput = Math.round(capacity * (0.6 + Math.random() * 0.2) * 10) / 10;
    } else if (status === "error") {
      currentOutput = Math.round(capacity * Math.random() * 0.2 * 10) / 10;
      todayEnergy =
        Math.round(currentOutput * (1 + Math.random() * 2) * 10) / 10;
      peakOutput = Math.round(capacity * (0.2 + Math.random() * 0.2) * 10) / 10;
    }

    // Generate a random install date within the last 3 years
    const now = new Date();
    const threeYearsAgo = new Date(
      now.getFullYear() - 3,
      now.getMonth(),
      now.getDate()
    );
    const randomTimestamp =
      threeYearsAgo.getTime() +
      Math.random() * (now.getTime() - threeYearsAgo.getTime());
    const installDate = new Date(randomTimestamp);
    const formattedDate = installDate.toISOString().split("T")[0];

    // Create the plant object
    const plant = {
      id: `plant${baseCount + i + 11}`,
      name: `${region.name} Solar Plant ${i + 1}`,
      status: status,
      capacity: capacity,
      currentOutput: currentOutput,
      todayEnergy: todayEnergy,
      peakOutput: peakOutput,
      installDate: formattedDate,
      location: region.name,
      latitude: lat,
      longitude: lng,
      region: region.name.toLowerCase().replace(" thailand", ""),
    };

    additionalPlants.push(plant);
  }

  return additionalPlants;
}

// Add the generated plants to our sample data
const additionalPlants = generateAdditionalPlants(100);
const plantsData = [...solarPlantsData, ...additionalPlants];

// Make the data available to other scripts
window.plantsData = plantsData;

// Initialize the map when the DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Make sure the Leaflet container is visible and the Thailand container is hidden
  const leafletContainer = document.getElementById("leaflet-map-container");
  if (leafletContainer) {
    leafletContainer.classList.remove("hidden");
  }

  const thailandContainer = document.getElementById("thailand-map-container");
  if (thailandContainer) {
    thailandContainer.classList.add("hidden");
  }

  // Ensure satellite tab is active
  const satelliteTab = document.getElementById("satellite-tab");
  if (satelliteTab) {
    satelliteTab.classList.add("bg-blue-600", "text-white");
    satelliteTab.classList.remove("bg-white", "text-gray-700");
  }

  // Set world map button as active
  const worldMapBtn = document.getElementById("world-map-btn");
  if (worldMapBtn) {
    worldMapBtn.classList.add("bg-blue-600", "text-white");
    worldMapBtn.classList.remove("bg-gray-100", "text-gray-800");
  }
});
