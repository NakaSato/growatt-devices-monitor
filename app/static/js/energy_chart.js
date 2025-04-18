/**
 * Energy Chart Utilities
 * A collection of utility functions for creating and managing charts
 * in the Growatt API dashboard.
 */

// Register Chart.js plugins if available
document.addEventListener("DOMContentLoaded", function () {
  if (typeof Chart !== "undefined" && typeof ChartDataLabels !== "undefined") {
    Chart.register(ChartDataLabels);
  }
});

/**
 * Chart Color Themes
 */
const chartColors = {
  primary: {
    base: "rgba(16, 185, 129, 1)",
    light: "rgba(16, 185, 129, 0.2)",
  },
  secondary: {
    base: "rgba(59, 130, 246, 1)",
    light: "rgba(59, 130, 246, 0.2)",
  },
  tertiary: {
    base: "rgba(249, 115, 22, 1)",
    light: "rgba(249, 115, 22, 0.2)",
  },
  quaternary: {
    base: "rgba(139, 92, 246, 1)",
    light: "rgba(139, 92, 246, 0.2)",
  },
  quinary: {
    base: "rgba(236, 72, 153, 1)",
    light: "rgba(236, 72, 153, 0.2)",
  },
  grid: "rgba(243, 244, 246, 0.7)",
  text: "#6b7280",
  primaryEnhanced: {
    base: "rgba(16, 185, 129, 0.8)",
    light: "rgba(16, 185, 129, 0.1)",
    hover: "rgba(16, 185, 129, 1)",
  },
  secondaryEnhanced: {
    base: "rgba(59, 130, 246, 0.8)",
    light: "rgba(59, 130, 246, 0.1)",
    hover: "rgba(59, 130, 246, 1)",
  },
  tertiaryEnhanced: {
    base: "rgba(249, 115, 22, 0.8)",
    light: "rgba(249, 115, 22, 0.1)",
    hover: "rgba(249, 115, 22, 1)",
  },
};

/**
 * Energy Data Utilities
 */
const EnergyDataUtils = {
  /**
   * Generates realistic energy production data based on period and time
   * @param {string} period - 'day', 'week', 'month', or 'year'
   * @param {number} capacity - System capacity in kW
   * @param {Date} date - Reference date for season adjustments
   * @returns {Object} Generated energy data with labels and datasets
   */
  generateEnergyData(period = "day", capacity = 10, date = new Date()) {
    let labels = [];
    let production = [];
    let consumption = [];
    let gridExchange = [];

    const month = date.getMonth(); // 0-11
    const seasonalFactor = this.getSeasonalFactor(month);

    switch (period) {
      case "day":
        labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
        production = this.generateDailyProduction(
          labels.length,
          capacity,
          seasonalFactor
        );
        consumption = this.generateDailyConsumption(labels.length);
        break;
      case "week":
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        production = this.generateWeeklyProduction(
          labels.length,
          capacity,
          seasonalFactor
        );
        consumption = this.generateWeeklyConsumption(labels.length);
        break;
      case "month":
        // Generate days in month
        const daysInMonth = new Date(
          date.getFullYear(),
          date.getMonth() + 1,
          0
        ).getDate();
        labels = Array.from({ length: daysInMonth }, (_, i) => `${i + 1}`);
        production = this.generateMonthlyProduction(
          labels.length,
          capacity,
          seasonalFactor
        );
        consumption = this.generateMonthlyConsumption(labels.length);
        break;
      case "year":
        labels = [
          "Jan",
          "Feb",
          "Mar",
          "Apr",
          "May",
          "Jun",
          "Jul",
          "Aug",
          "Sep",
          "Oct",
          "Nov",
          "Dec",
        ];
        production = this.generateYearlyProduction(labels.length, capacity);
        consumption = this.generateYearlyConsumption(labels.length);
        break;
    }

    // Calculate grid exchange (negative = export to grid, positive = import from grid)
    gridExchange = consumption.map((cons, i) => {
      return +(cons - production[i]).toFixed(2);
    });

    // Calculate totals
    const totalProduction = production.reduce((a, b) => a + b, 0).toFixed(2);
    const totalConsumption = consumption.reduce((a, b) => a + b, 0).toFixed(2);
    const totalGridImport = gridExchange
      .filter((val) => val > 0)
      .reduce((a, b) => a + b, 0)
      .toFixed(2);
    const totalGridExport = Math.abs(
      gridExchange
        .filter((val) => val < 0)
        .reduce((a, b) => a + b, 0)
        .toFixed(2)
    );
    const selfConsumption = (totalProduction - totalGridExport).toFixed(2);

    return {
      labels,
      datasets: {
        production,
        consumption,
        gridExchange,
      },
      totals: {
        production: totalProduction,
        consumption: totalConsumption,
        selfConsumption: selfConsumption,
        gridImport: totalGridImport,
        gridExport: totalGridExport,
      },
      percentages: {
        selfConsumption: ((selfConsumption / totalProduction) * 100).toFixed(1),
        gridExport: ((totalGridExport / totalProduction) * 100).toFixed(1),
        gridImport: ((totalGridImport / totalConsumption) * 100).toFixed(1),
      },
    };
  },

  /**
   * Get seasonal adjustment factor based on month
   * @param {number} month - Month index (0-11)
   * @returns {number} Seasonal factor (0.5-1.5)
   */
  getSeasonalFactor(month) {
    // Northern hemisphere seasonal pattern
    const seasonalPatterns = [
      0.6, // January
      0.7, // February
      0.9, // March
      1.1, // April
      1.3, // May
      1.4, // June
      1.5, // July
      1.4, // August
      1.2, // September
      0.9, // October
      0.7, // November
      0.5, // December
    ];

    return seasonalPatterns[month];
  },

  /**
   * Generate daily production curve with realistic pattern
   * @param {number} points - Number of data points (hours)
   * @param {number} capacity - System capacity in kW
   * @param {number} seasonalFactor - Seasonal adjustment (0.5-1.5)
   * @returns {Array} Hourly production values
   */
  generateDailyProduction(points, capacity, seasonalFactor) {
    return Array.from({ length: points }, (_, hour) => {
      // No production at night (6am-8pm production window)
      if (hour < 6 || hour > 20) return 0;

      // Bell curve peaking at solar noon (1pm)
      const peakHour = 13;
      const hourFactor = Math.max(0, 1 - Math.pow((hour - peakHour) / 7, 2));

      // Add some variability (clouds, etc.)
      const variability = 0.85 + Math.random() * 0.3;

      // Calculate value with capacity, seasonal and hourly factors
      let value = capacity * seasonalFactor * hourFactor * variability;

      // Round to 2 decimal places
      return +value.toFixed(2);
    });
  },

  /**
   * Generate daily consumption pattern
   * @param {number} points - Number of data points (hours)
   * @returns {Array} Hourly consumption values
   */
  generateDailyConsumption(points) {
    return Array.from({ length: points }, (_, hour) => {
      // Base load
      let baseLoad = 0.5;

      // Morning peak (6-9am)
      if (hour >= 6 && hour < 9) {
        baseLoad += 1.5 * (1 - Math.abs(hour - 7.5) / 1.5);
      }

      // Evening peak (18-22)
      if (hour >= 18 && hour < 22) {
        baseLoad += 2 * (1 - Math.abs(hour - 20) / 2);
      }

      // Night trough
      if (hour >= 0 && hour < 5) {
        baseLoad += 0.2;
      }

      // Add variability
      const variability = 0.9 + Math.random() * 0.2;

      // Calculate value
      let value = baseLoad * variability;

      // Round to 2 decimal places
      return +value.toFixed(2);
    });
  },

  /**
   * Generate weekly production with weekend variation
   */
  generateWeeklyProduction(points, capacity, seasonalFactor) {
    return Array.from({ length: points }, (_, day) => {
      // Weekend variation (Saturday and Sunday, last two days)
      const isWeekend = day >= 5;
      const weekendFactor = isWeekend ? 1 : 0.95;

      // Weather variation (random cloudy day)
      const weatherFactor = Math.random() > 0.25 ? 1 : 0.6;

      // Base daily production (simplified)
      const baseProduction =
        capacity * 5 * seasonalFactor * weekendFactor * weatherFactor;

      // Add variability
      const variability = 0.9 + Math.random() * 0.2;

      // Calculate and round value
      return +(baseProduction * variability).toFixed(2);
    });
  },

  /**
   * Generate weekly consumption with weekend variation
   */
  generateWeeklyConsumption(points) {
    return Array.from({ length: points }, (_, day) => {
      // Weekend variation (Saturday and Sunday, last two days)
      const isWeekend = day >= 5;
      const weekendFactor = isWeekend ? 1.2 : 1;

      // Base daily consumption
      const baseConsumption = 12 * weekendFactor;

      // Add variability
      const variability = 0.9 + Math.random() * 0.2;

      // Calculate and round value
      return +(baseConsumption * variability).toFixed(2);
    });
  },

  /**
   * Generate monthly production with day-of-month variations
   */
  generateMonthlyProduction(days, capacity, seasonalFactor) {
    return Array.from({ length: days }, (_, day) => {
      // Generate weather patterns (clusters of good/bad days)
      const weatherPattern = Math.sin(day / 3) * 0.25 + 0.75;

      // Weekend effect (higher consumption on weekends)
      const dayOfWeek = day % 7;
      const isWeekend = dayOfWeek >= 5;
      const weekendFactor = isWeekend ? 1.05 : 1;

      // Base production
      const baseProduction =
        capacity * 5 * seasonalFactor * weatherPattern * weekendFactor;

      // Add variability
      const variability = 0.9 + Math.random() * 0.2;

      // Calculate and round value
      return +(baseProduction * variability).toFixed(2);
    });
  },

  /**
   * Generate monthly consumption with day-of-month variations
   */
  generateMonthlyConsumption(days) {
    return Array.from({ length: days }, (_, day) => {
      // Weekend effect (higher consumption on weekends)
      const dayOfWeek = day % 7;
      const isWeekend = dayOfWeek >= 5;
      const weekendFactor = isWeekend ? 1.25 : 1;

      // Base consumption
      const baseConsumption = 12 * weekendFactor;

      // Add variability
      const variability = 0.9 + Math.random() * 0.2;

      // Calculate and round value
      return +(baseConsumption * variability).toFixed(2);
    });
  },

  /**
   * Generate yearly production with seasonal variations
   */
  generateYearlyProduction(months, capacity) {
    return Array.from({ length: months }, (_, month) => {
      // Seasonal factor by month
      const seasonalFactor = this.getSeasonalFactor(month);

      // Monthly base (approximately 30 days)
      const baseProduction = capacity * 5 * seasonalFactor * 30;

      // Add variability
      const variability = 0.9 + Math.random() * 0.2;

      // Calculate and round value
      return +(baseProduction * variability).toFixed(2);
    });
  },

  /**
   * Generate yearly consumption with seasonal variations
   */
  generateYearlyConsumption(months) {
    return Array.from({ length: months }, (_, month) => {
      // Seasonal consumption pattern (higher in winter and summer)
      const winterEffect = Math.cos((month / 11) * 2 * Math.PI) * 0.3 + 0.7;
      const summerEffect = Math.sin((month / 11) * 2 * Math.PI) * 0.2 + 0.8;
      const seasonalFactor = winterEffect + summerEffect;

      // Monthly base (approximately 30 days)
      const baseConsumption = 12 * 30 * seasonalFactor;

      // Add variability
      const variability = 0.95 + Math.random() * 0.1;

      // Calculate and round value
      return +(baseConsumption * variability).toFixed(2);
    });
  },
};

// Export utilities to global scope
window.EnergyDataUtils = EnergyDataUtils;

/**
 * Chart Creation Functions
 */

// Create a line chart
function createLineChart(elementId, data, options = {}) {
  const canvas = document.getElementById(elementId);
  if (!canvas) {
    console.error(`Canvas element with ID '${elementId}' not found`);
    return null;
  }

  const ctx = canvas.getContext("2d");

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      datalabels: {
        display: false,
      },
      legend: {
        position: "top",
        labels: {
          usePointStyle: true,
          padding: 15,
        },
      },
      tooltip: {
        enabled: true,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          color: chartColors.grid,
          drawBorder: false,
        },
        ticks: {
          padding: 10,
          color: chartColors.text,
          font: { size: 11 },
        },
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          padding: 10,
          color: chartColors.text,
          font: { size: 11 },
        },
      },
    },
  };

  // Merge with custom options
  const chartOptions = { ...defaultOptions, ...options };

  try {
    return new Chart(ctx, {
      type: "line",
      data: data,
      options: chartOptions,
    });
  } catch (error) {
    console.error("Error creating line chart:", error);
    return null;
  }
}

// Create a doughnut/pie chart
function createDonutChart(elementId, series, labels, options = {}) {
  if (typeof ApexCharts === "undefined") {
    console.error("ApexCharts library not loaded");
    return null;
  }

  const element = document.getElementById(elementId);
  if (!element) {
    console.error(`Element with ID '${elementId}' not found`);
    return null;
  }

  const defaultOptions = {
    series: series,
    labels: labels,
    chart: {
      type: "donut",
      height: 300,
    },
    colors: [
      chartColors.primary.base,
      chartColors.tertiary.base,
      chartColors.secondary.base,
    ],
    plotOptions: {
      pie: {
        donut: {
          size: "65%",
          labels: {
            show: true,
            name: { show: true },
            value: {
              show: true,
              formatter: function (val) {
                return val + " kWh";
              },
            },
            total: {
              show: true,
              label: "Total Energy",
              formatter: function (w) {
                return (
                  w.globals.seriesTotals.reduce((a, b) => a + b, 0) + " kWh"
                );
              },
            },
          },
        },
      },
    },
    dataLabels: { enabled: false },
    legend: {
      position: "bottom",
      offsetY: 0,
    },
    tooltip: {
      y: {
        formatter: function (val) {
          return val + " kWh";
        },
      },
    },
    stroke: { width: 2 },
    responsive: [
      {
        breakpoint: 480,
        options: {
          chart: { height: 250 },
          legend: { position: "bottom" },
        },
      },
    ],
  };

  // Merge options
  const chartOptions = { ...defaultOptions, ...options };

  try {
    const chart = new ApexCharts(element, chartOptions);
    chart.render();
    return chart;
  } catch (error) {
    console.error("Error creating donut chart:", error);
    return null;
  }
}

// Create dataset object for Chart.js
function createDataset(label, data, color = "primary", options = {}) {
  const colorSet = chartColors[color] || chartColors.primary;

  return {
    label: label,
    data: data,
    backgroundColor: colorSet.light,
    borderColor: colorSet.base,
    borderWidth: 2,
    fill: true,
    tension: 0.4,
    pointRadius: 2,
    ...options,
  };
}

/**
 * Energy Yield Overview Chart Functions
 */
const EnergyYieldChart = {
  /**
   * Initialize energy yield overview chart
   * @param {string} elementId - Canvas element ID
   * @param {Object} data - Chart data object with labels and datasets
   * @returns {Object} Chart instance
   */
  createEnergyYieldChart(elementId, data) {
    const canvas = document.getElementById(elementId);
    if (!canvas) {
      console.error(`Canvas element with ID '${elementId}' not found`);
      return null;
    }

    const ctx = canvas.getContext("2d");

    // Prepare datasets with enhanced styling
    const datasets = [
      {
        label: "Energy Production (kWh)",
        data: data.datasets.production,
        backgroundColor:
          chartColors.primaryEnhanced.light || "rgba(16, 185, 129, 0.1)",
        borderColor:
          chartColors.primaryEnhanced.base || "rgba(16, 185, 129, 0.8)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor:
          chartColors.primaryEnhanced.hover || "rgba(16, 185, 129, 1)",
        pointHoverBackgroundColor: "#ffffff",
        pointBorderColor:
          chartColors.primaryEnhanced.hover || "rgba(16, 185, 129, 1)",
        pointHoverBorderColor:
          chartColors.primaryEnhanced.hover || "rgba(16, 185, 129, 1)",
        pointBorderWidth: 2,
        pointHoverBorderWidth: 2,
      },
      {
        label: "Energy Consumption (kWh)",
        data: data.datasets.consumption,
        backgroundColor:
          chartColors.tertiaryEnhanced.light || "rgba(249, 115, 22, 0.1)",
        borderColor:
          chartColors.tertiaryEnhanced.base || "rgba(249, 115, 22, 0.8)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor:
          chartColors.tertiaryEnhanced.hover || "rgba(249, 115, 22, 1)",
        pointHoverBackgroundColor: "#ffffff",
        pointBorderColor:
          chartColors.tertiaryEnhanced.hover || "rgba(249, 115, 22, 1)",
        pointHoverBorderColor:
          chartColors.tertiaryEnhanced.hover || "rgba(249, 115, 22, 1)",
        pointBorderWidth: 2,
        pointHoverBorderWidth: 2,
      },
      {
        label: "Grid Exchange (kWh)",
        data: data.datasets.gridExchange,
        backgroundColor:
          chartColors.secondaryEnhanced.light || "rgba(59, 130, 246, 0.1)",
        borderColor:
          chartColors.secondaryEnhanced.base || "rgba(59, 130, 246, 0.8)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor:
          chartColors.secondaryEnhanced.hover || "rgba(59, 130, 246, 1)",
        pointHoverBackgroundColor: "#ffffff",
        pointBorderColor:
          chartColors.secondaryEnhanced.hover || "rgba(59, 130, 246, 1)",
        pointHoverBorderColor:
          chartColors.secondaryEnhanced.hover || "rgba(59, 130, 246, 1)",
        pointBorderWidth: 2,
        pointHoverBorderWidth: 2,
      },
    ];

    // Enhanced chart configuration with light theme styling
    const chartConfig = {
      type: "line",
      data: {
        labels: data.labels,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            position: "bottom",
            align: "center",
            labels: {
              usePointStyle: true,
              padding: 20,
              boxWidth: 10,
              boxHeight: 10,
              font: {
                size: 12,
                family:
                  'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              },
            },
            title: {
              padding: {
                bottom: 10,
              },
            },
          },
          tooltip: {
            backgroundColor: "rgba(255, 255, 255, 0.95)",
            titleColor: "#111827",
            bodyColor: "#374151",
            borderColor: "rgba(229, 231, 235, 1)",
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            titleFont: {
              weight: "bold",
              size: 13,
            },
            bodyFont: {
              size: 12,
            },
            displayColors: true,
            boxWidth: 8,
            boxHeight: 8,
            usePointStyle: true,
            callbacks: {
              label: function (context) {
                let label = context.dataset.label || "";
                if (label) {
                  label += ": ";
                }
                if (context.parsed.y !== null) {
                  label += context.parsed.y.toFixed(2) + " kWh";
                }
                return label;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(243, 244, 246, 0.8)",
              lineWidth: 1,
              drawBorder: false,
            },
            border: {
              display: false,
            },
            ticks: {
              padding: 10,
              color: "#6B7280",
              font: {
                size: 11,
              },
            },
            title: {
              display: true,
              text: "Energy (kWh)",
              color: "#374151",
              font: {
                size: 12,
                weight: "normal",
              },
              padding: {
                bottom: 10,
              },
            },
          },
          x: {
            grid: {
              display: false,
              drawBorder: false,
            },
            border: {
              display: false,
            },
            ticks: {
              padding: 10,
              color: "#6B7280",
              font: {
                size: 11,
              },
              maxRotation: 45,
              minRotation: 0,
            },
          },
        },
        layout: {
          padding: {
            top: 10,
            right: 16,
            bottom: 10,
            left: 10,
          },
        },
        elements: {
          line: {
            borderJoinStyle: "round",
          },
        },
        animation: {
          duration: 1000,
          easing: "easeOutQuart",
        },
      },
    };

    try {
      return new Chart(ctx, chartConfig);
    } catch (error) {
      console.error("Error creating energy yield chart:", error);
      return null;
    }
  },

  /**
   * Update chart data with new period
   * @param {Object} chartInstance - Chart.js chart instance
   * @param {string} period - Time period (day, week, month, year)
   * @param {number} capacity - System capacity in kW
   */
  updateChartPeriod(chartInstance, period, capacity = 10) {
    if (!chartInstance) {
      console.error("No valid chart instance provided");
      return;
    }

    // Generate new data
    const energyData = EnergyDataUtils.generateEnergyData(period, capacity);

    // Update chart data
    chartInstance.data.labels = energyData.labels;
    chartInstance.data.datasets[0].data = energyData.datasets.production;
    chartInstance.data.datasets[1].data = energyData.datasets.consumption;
    chartInstance.data.datasets[2].data = energyData.datasets.gridExchange;

    // Update chart
    chartInstance.update();

    return energyData;
  },
};

/**
 * Process weather data for chart display
 * @param {Array} weatherData - Array of weather data objects
 * @param {string} metric - The weather metric to display (temperature, humidity, weather)
 * @param {string} period - The time period to display (day, week, month)
 * @returns {Object} Processed data with labels and values
 */
function processWeatherData(weatherData, metric, period) {
  if (!weatherData || !weatherData.length) {
    return { labels: [], values: [] };
  }

  let labels = [];
  let values = [];

  // Sort data by timestamp
  const sortedData = [...weatherData].sort((a, b) => {
    return new Date(a.last_update_time) - new Date(b.last_update_time);
  });

  // Filter data based on the period
  const now = new Date();
  let filteredData = sortedData;

  switch (period) {
    case "day":
      // Filter for today only
      filteredData = sortedData.filter((item) => {
        const itemDate = new Date(item.last_update_time);
        return itemDate.setHours(0, 0, 0, 0) === now.setHours(0, 0, 0, 0);
      });
      break;
    case "week":
      // Filter for the last 7 days
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      filteredData = sortedData.filter((item) => {
        const itemDate = new Date(item.last_update_time);
        return itemDate >= weekAgo;
      });
      break;
    case "month":
      // Filter for the current month
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
      filteredData = sortedData.filter((item) => {
        const itemDate = new Date(item.last_update_time);
        return itemDate >= monthStart;
      });
      break;
  }

  // Process data based on the metric
  filteredData.forEach((item) => {
    // Extract time from timestamp for label
    const date = new Date(item.last_update_time);
    const timeLabel = date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    let value = null;

    switch (metric) {
      case "temperature":
        // Extract numeric value from temperature string
        value = parseFloat(String(item.temperature).replace(/[^\d.-]/g, ""));
        break;
      case "humidity":
        // Extract numeric value from humidity string
        value = parseFloat(String(item.humidity).replace(/[^\d.-]/g, ""));
        break;
      case "weather":
        // For weather conditions, we might use a numeric mapping
        // This depends on how you want to visualize weather conditions
        const weatherMapping = {
          Sunny: 10,
          Clear: 9,
          "Partly Cloudy": 7,
          Cloudy: 5,
          Overcast: 4,
          Rain: 3,
          "Heavy Rain": 1,
          Storm: 0,
        };
        value =
          weatherMapping[item.weather] !== undefined
            ? weatherMapping[item.weather]
            : 5;
        break;
    }

    if (value !== null && !isNaN(value)) {
      labels.push(timeLabel);
      values.push(value);
    }
  });

  // If we have too many data points, sample them
  if (labels.length > 24) {
    const sampledData = sampleDataPoints(labels, values, 24);
    return sampledData;
  }

  return { labels, values };
}

/**
 * Sample data points to reduce the number of points on a chart
 * @param {Array} labels - Array of labels
 * @param {Array} values - Array of values
 * @param {number} targetCount - Target number of data points
 * @returns {Object} Sampled data with labels and values
 */
function sampleDataPoints(labels, values, targetCount) {
  if (labels.length <= targetCount) {
    return { labels, values };
  }

  const sampledLabels = [];
  const sampledValues = [];
  const step = Math.ceil(labels.length / targetCount);

  for (let i = 0; i < labels.length; i += step) {
    sampledLabels.push(labels[i]);
    sampledValues.push(values[i]);

    if (sampledLabels.length >= targetCount) {
      break;
    }
  }

  return { labels: sampledLabels, values: sampledValues };
}

/**
 * Format date object for chart display
 * @param {Date} date - The date to format
 * @param {string} period - The time period (day, week, month, year)
 * @returns {string} Formatted date string appropriate for the time period
 */
function formatChartDate(date, period = "day") {
  if (!date || !(date instanceof Date)) {
    return "";
  }

  switch (period) {
    case "day":
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    case "week":
      return date.toLocaleDateString([], {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
    case "month":
      return date.toLocaleDateString([], { month: "short", day: "numeric" });
    case "year":
      return date.toLocaleDateString([], { month: "short", year: "numeric" });
    default:
      return date.toLocaleDateString();
  }
}

// Export the function for use in the EnergyCharts object
if (typeof window !== "undefined" && window.EnergyCharts) {
  window.EnergyCharts.processWeatherData = processWeatherData;
}

// Add a debug function to test if the library is properly loaded
window.EnergyChartDebug = {
  test: function () {
    console.log("EnergyChart library is properly loaded and initialized");
    return true;
  },
  generateTestData: function () {
    return EnergyDataUtils.generateEnergyData("day", 10);
  },
};

// Make sure EnergyDataUtils is exported properly
window.EnergyDataUtils = EnergyDataUtils;

// Signal that the library has loaded
console.log("Energy chart library loaded successfully");

// Export functions for use in other scripts
window.EnergyCharts = {
  // Chart creation
  createLineChart,
  createDonutChart,
  createDataset,
  createEnergyYieldChart: EnergyYieldChart.createEnergyYieldChart,
  updateEnergyYieldChart: EnergyYieldChart.updateChartPeriod,

  // Data utilities
  generateEnergyData: EnergyDataUtils.generateEnergyData.bind(EnergyDataUtils),
  processWeatherData,
  formatChartDate,

  // Styling
  colors: chartColors,
};
