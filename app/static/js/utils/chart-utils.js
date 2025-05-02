/**
 * Utility functions for creating and managing charts
 */
const ChartUtils = {
  /**
   * Create a line chart
   * @param {string} canvasId - ID of the canvas element
   * @param {Array} labels - Labels for the x-axis
   * @param {Array} datasets - Chart datasets
   * @param {Object} options - Additional chart options
   * @returns {Chart} The created Chart instance
   */
  createLineChart(canvasId, labels, datasets, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext("2d");

    // Default options for line charts
    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
        },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 10,
          },
        },
        y: {
          beginAtZero: true,
        },
      },
    };

    // Merge default options with custom options
    const chartOptions = { ...defaultOptions, ...options };

    // Create and return the chart
    return new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: datasets,
      },
      options: chartOptions,
    });
  },

  /**
   * Create a bar chart
   * @param {string} canvasId - ID of the canvas element
   * @param {Array} labels - Labels for the x-axis
   * @param {Array} datasets - Chart datasets
   * @param {Object} options - Additional chart options
   * @returns {Chart} The created Chart instance
   */
  createBarChart(canvasId, labels, datasets, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext("2d");

    // Default options for bar charts
    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
        },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 0,
          },
        },
        y: {
          beginAtZero: true,
        },
      },
    };

    // Merge default options with custom options
    const chartOptions = { ...defaultOptions, ...options };

    // Create and return the chart
    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: datasets,
      },
      options: chartOptions,
    });
  },

  /**
   * Create a pie chart
   * @param {string} canvasId - ID of the canvas element
   * @param {Array} labels - Chart labels
   * @param {Array} data - Chart data values
   * @param {Array} backgroundColor - Background colors for segments
   * @param {Object} options - Additional chart options
   * @returns {Chart} The created Chart instance
   */
  createPieChart(canvasId, labels, data, backgroundColor, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext("2d");

    // Default options for pie charts
    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
        },
      },
    };

    // Merge default options with custom options
    const chartOptions = { ...defaultOptions, ...options };

    // Create and return the chart
    return new Chart(ctx, {
      type: "pie",
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: backgroundColor,
          },
        ],
      },
      options: chartOptions,
    });
  },

  /**
   * Update an existing chart with new data
   * @param {Chart} chart - The Chart instance to update
   * @param {Array} labels - New labels
   * @param {Array} datasets - New datasets
   */
  updateChart(chart, labels, datasets) {
    if (!chart) return;

    chart.data.labels = labels;
    chart.data.datasets = datasets;
    chart.update();
  },

  /**
   * Generate random colors for charts
   * @param {number} count - Number of colors to generate
   * @returns {Array} Array of color strings
   */
  generateColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
      // Generate colors with good saturation and brightness
      const hue = (i * 137) % 360; // Golden angle approximation for better distribution
      colors.push(`hsl(${hue}, 70%, 60%)`);
    }
    return colors;
  },
};

// Make available globally
window.ChartUtils = ChartUtils;
