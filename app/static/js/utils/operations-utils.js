/**
 * Operations Utilities for Solar System Monitoring
 * Provides utility functions for operations management and solar system configuration
 */

// Initialize sample data if not defined elsewhere
function initializeData() {
  // Initialize sample plants if not defined
  if (typeof window.samplePlants === 'undefined') {
    window.samplePlants = [
      {
        id: 'plant-001',
        name: 'Sunnyvale Energy Park',
        location: 'Sunnyvale, CA',
        capacity: 85.5,
        status: 'normal',
        lastReported: '2023-09-15T10:30:00Z',
        devices: 12,
        activeAlerts: 0
      },
      {
        id: 'plant-002',
        name: 'Desert Sun Array',
        location: 'Phoenix, AZ',
        capacity: 120.2,
        status: 'warning',
        lastReported: '2023-09-15T09:45:00Z',
        devices: 18,
        activeAlerts: 2
      },
      {
        id: 'plant-003',
        name: 'Mountain View Solar',
        location: 'Boulder, CO',
        capacity: 42.8,
        status: 'normal',
        lastReported: '2023-09-15T10:15:00Z',
        devices: 8,
        activeAlerts: 0
      }
    ];
  }

  // Initialize sample maintenance tasks if not defined
  if (typeof window.sampleMaintenanceTasks === 'undefined') {
    window.sampleMaintenanceTasks = [
      {
        id: 'task-001',
        title: 'Inverter Replacement',
        plantId: 'plant-001',
        plantName: 'Sunnyvale Energy Park',
        status: 'scheduled',
        priority: 'high',
        dueDate: '2023-10-05',
        assignedTo: 'John Doe',
        description: 'Replace faulty inverter on string 3.'
      },
      {
        id: 'task-002',
        title: 'Panel Cleaning',
        plantId: 'plant-002',
        plantName: 'Desert Sun Array',
        status: 'in-progress',
        priority: 'medium',
        dueDate: '2023-09-20',
        assignedTo: 'Maria Garcia',
        description: 'Clean dust accumulation on all panels in section A.'
      }
    ];
  }

  // Initialize alerts if not defined
  if (typeof window.sampleAlerts === 'undefined') {
    window.sampleAlerts = [
      {
        id: 'alert-001',
        plantId: 'plant-002',
        plantName: 'Desert Sun Array',
        type: 'error',
        message: 'Inverter communication lost',
        deviceId: 'INV-002-05',
        timestamp: '2023-09-15T08:30:00Z',
        resolved: false
      },
      {
        id: 'alert-002',
        plantId: 'plant-002',
        plantName: 'Desert Sun Array',
        type: 'warning',
        message: 'Low energy production',
        deviceId: 'STR-002-03',
        timestamp: '2023-09-15T09:15:00Z',
        resolved: false
      }
    ];
  }
}

// Format energy values with proper units (kWh, MWh)
function formatEnergyValue(value, decimals = 2) {
  if (value === null || value === undefined) return "N/A";

  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(decimals)} MWh`;
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(decimals)} kWh`;
  } else {
    return `${value.toFixed(decimals)} Wh`;
  }
}

// Format power values with proper units (W, kW, MW)
function formatPowerValue(value, decimals = 2) {
  if (value === null || value === undefined) return "N/A";

  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(decimals)} MW`;
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(decimals)} kW`;
  } else {
    return `${value.toFixed(decimals)} W`;
  }
}

// Calculate performance ratio (PR)
function calculatePerformanceRatio(actualEnergy, theoreticalEnergy) {
  if (!actualEnergy || !theoreticalEnergy || theoreticalEnergy === 0) {
    return null;
  }

  const ratio = (actualEnergy / theoreticalEnergy) * 100;
  return Math.min(100, ratio); // Cap at 100%
}

// Calculate specific yield (kWh/kWp)
function calculateSpecificYield(energyProduced, installedCapacity) {
  if (!energyProduced || !installedCapacity || installedCapacity === 0) {
    return null;
  }

  return energyProduced / installedCapacity;
}

// Generate a color based on the performance value (green for good, red for bad)
function getPerformanceColor(value, thresholdLow = 70, thresholdMedium = 90) {
  if (value === null || value === undefined) return "#9CA3AF"; // gray-400

  if (value >= thresholdMedium) {
    return "#10B981"; // green-500
  } else if (value >= thresholdLow) {
    return "#F59E0B"; // amber-500
  } else {
    return "#EF4444"; // red-500
  }
}

// Calculate solar system savings
function calculateSavings(energyProduced, electricityRate) {
  if (!energyProduced || !electricityRate) {
    return null;
  }

  return energyProduced * electricityRate;
}

// Calculate CO2 emissions avoided (kg)
function calculateCO2Avoided(energyProduced, emissionFactor = 0.5) {
  // Default: 0.5 kg CO2/kWh
  if (!energyProduced) {
    return null;
  }

  return energyProduced * emissionFactor;
}

// Generate chart configuration for solar production
function generateSolarProductionChart(elementId, data) {
  const ctx = document.getElementById(elementId).getContext("2d");

  // Parse dates and ensure data is chronologically sorted
  const sortedData = [...data].sort(
    (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
  );

  // Extract timestamps and energy values
  const labels = sortedData.map((item) => {
    const date = new Date(item.timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  });

  const powerValues = sortedData.map((item) => item.power);
  const energyValues = sortedData.map((item) => item.energy);

  return new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Power (kW)",
          data: powerValues,
          borderColor: "#3B82F6", // blue-500
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          borderWidth: 2,
          tension: 0.2,
          yAxisID: "y",
        },
        {
          label: "Energy (kWh)",
          data: energyValues,
          borderColor: "#10B981", // green-500
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          borderWidth: 2,
          tension: 0.2,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      interaction: {
        mode: "index",
        intersect: false,
      },
      scales: {
        y: {
          type: "linear",
          display: true,
          position: "left",
          title: {
            display: true,
            text: "Power (kW)",
          },
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "Energy (kWh)",
          },
          grid: {
            drawOnChartArea: false,
          },
        },
      },
    },
  });
}

// Generate report data for system operations
function generateOperationsReport() {
  // This would typically fetch data from API and generate a report
  // For now, we'll simulate with a download
  const reportData = {
    timestamp: new Date().toISOString(),
    system: "Growatt Monitoring System",
    plants: [],
    devices: [],
    performance: {},
    alerts: [],
  };

  const jsonString = JSON.stringify(reportData, null, 2);
  const blob = new Blob([jsonString], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  // Create link and trigger download
  const a = document.createElement("a");
  a.href = url;
  a.download = `operations_report_${new Date()
    .toISOString()
    .slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Initialize data when the script loads
document.addEventListener('DOMContentLoaded', function() {
  initializeData();
});

// Export utilities
window.OperationsUtils = {
  initializeData,
  formatEnergyValue,
  formatPowerValue,
  calculatePerformanceRatio,
  calculateSpecificYield,
  getPerformanceColor,
  calculateSavings,
  calculateCO2Avoided,
  generateSolarProductionChart,
  generateOperationsReport,
};
