/**
 * Energy Chart Utilities
 * 
 * A collection of utilities for processing and visualizing energy data
 * with an engineering focus on data quality and advanced analytics.
 */

// Main namespace for Energy Chart utilities
window.EnergyDataUtils = {};
window.EnergyCharts = {};

/**
 * Data Processing Functions
 */
window.EnergyDataUtils = {
  /**
   * Cleans and validates energy data
   * @param {Object} data - Raw energy data object
   * @returns {Object} - Cleaned data
   */
  cleanData: function(data) {
    if (!data || !data.datasets || !data.labels) {
      console.error('Invalid data format');
      return null;
    }
    
    const cleanedData = {
      labels: data.labels,
      datasets: {}
    };
    
    // Keep track of totals and metadata
    if (data.totals) cleanedData.totals = data.totals;
    if (data.percentages) cleanedData.percentages = data.percentages;
    if (data.meta) cleanedData.meta = data.meta;
    
    // Clean each dataset by removing invalid values and interpolating missing values
    Object.keys(data.datasets).forEach(key => {
      const series = data.datasets[key];
      
      if (Array.isArray(series)) {
        cleanedData.datasets[key] = this.interpolateMissingValues(series);
      }
    });
    
    return cleanedData;
  },
  
  /**
   * Handle missing values using linear interpolation
   * @param {Array} data - Array of data points
   * @returns {Array} - Array with interpolated values
   */
  interpolateMissingValues: function(data) {
    if (!data || data.length === 0) return [];
    
    const result = [...data];
    
    // Find gaps (null or undefined values) and interpolate
    for (let i = 0; i < result.length; i++) {
      if (result[i] === null || result[i] === undefined) {
        // Look for previous valid value
        let prevIndex = i - 1;
        while (prevIndex >= 0 && (result[prevIndex] === null || result[prevIndex] === undefined)) {
          prevIndex--;
        }
        
        // Look for next valid value
        let nextIndex = i + 1;
        while (nextIndex < result.length && (result[nextIndex] === null || result[nextIndex] === undefined)) {
          nextIndex++;
        }
        
        // Interpolate if we have valid values on both sides
        if (prevIndex >= 0 && nextIndex < result.length) {
          const prevValue = result[prevIndex];
          const nextValue = result[nextIndex];
          const gap = nextIndex - prevIndex;
          const step = (nextValue - prevValue) / gap;
          
          result[i] = prevValue + step * (i - prevIndex);
        }
      }
    }
    
    return result;
  },
  
  /**
   * Calculate anomaly score for each data point
   * @param {Array} data - Array of data points
   * @returns {Array} - Array of anomaly scores (0-1, higher means more anomalous)
   */
  calculateAnomalyScores: function(data) {
    if (!data || data.length === 0) return [];
    
    // Filter out invalid values
    const validData = data.filter(val => val !== null && val !== undefined);
    if (validData.length === 0) return data.map(() => 0);
    
    // Calculate mean and standard deviation
    const mean = validData.reduce((sum, val) => sum + val, 0) / validData.length;
    const squaredDiffs = validData.map(val => Math.pow(val - mean, 2));
    const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / validData.length;
    const stdDev = Math.sqrt(variance);
    
    // Calculate z-score for each point, then convert to 0-1 scale
    return data.map(val => {
      if (val === null || val === undefined) return 0;
      if (stdDev === 0) return 0; // Avoid division by zero
      
      // Calculate absolute z-score
      const zScore = Math.abs((val - mean) / stdDev);
      
      // Convert to 0-1 scale using sigmoid function
      return 1 / (1 + Math.exp(-zScore + 3)); // +3 shifts the curve to flag only significant anomalies
    });
  },
  
  /**
   * Calculate moving average for a data series
   * @param {Array} data - Array of data points
   * @param {Number} window - Window size for moving average
   * @returns {Array} - Moving average values
   */
  calculateMovingAverage: function(data, window) {
    const result = [];
    
    for (let i = 0; i < data.length; i++) {
      if (i < window - 1) {
        // Not enough data points yet
        result.push(null);
      } else {
        // Calculate average of last 'window' points
        let sum = 0;
        let count = 0;
        
        for (let j = 0; j < window; j++) {
          const val = data[i - j];
          if (val !== null && val !== undefined) {
            sum += val;
            count++;
          }
        }
        
        result.push(count > 0 ? sum / count : null);
      }
    }
    
    return result;
  },
  
  /**
   * Calculate performance ratio (PR)
   * @param {Array} actualProduction - Array of actual production values
   * @param {Array} expectedProduction - Array of expected production values
   * @returns {Object} - PR stats including average, min, max
   */
  calculatePerformanceRatio: function(actualProduction, expectedProduction) {
    if (!actualProduction || !expectedProduction || 
        actualProduction.length !== expectedProduction.length) {
      return { average: null, min: null, max: null };
    }
    
    const prValues = [];
    
    for (let i = 0; i < actualProduction.length; i++) {
      const actual = actualProduction[i];
      const expected = expectedProduction[i];
      
      if (actual !== null && expected !== null && expected > 0) {
        prValues.push((actual / expected) * 100);
      }
    }
    
    if (prValues.length === 0) {
      return { average: null, min: null, max: null };
    }
    
    return {
      average: prValues.reduce((sum, val) => sum + val, 0) / prValues.length,
      min: Math.min(...prValues),
      max: Math.max(...prValues)
    };
  },
  
  /**
   * Calculate specific yield (kWh/kWp)
   * @param {Number} totalProduction - Total energy production in kWh
   * @param {Number} capacity - System capacity in kWp
   * @returns {Number} - Specific yield
   */
  calculateSpecificYield: function(totalProduction, capacity) {
    if (typeof totalProduction !== 'number' || typeof capacity !== 'number' || capacity <= 0) {
      return null;
    }
    
    return totalProduction / capacity;
  }
};

/**
 * Chart Creation and Configuration
 */
window.EnergyCharts = {
  /**
   * Create an energy yield chart with comparison to previous period
   * @param {String} canvasId - Canvas element ID
   * @param {Object} currentData - Current period data
   * @param {Object} prevPeriodData - Previous period data
   * @param {String} chartType - Chart type (bar, line, area)
   * @param {Object} options - Chart configuration options
   * @returns {Chart} - Chart.js instance
   */
  createEnergyYieldChart: function(canvasId, currentData, prevPeriodData, chartType, options) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      console.error("Chart canvas element not found!");
      return null;
    }
    
    // Process and clean the data
    const cleanCurrentData = window.EnergyDataUtils.cleanData(currentData);
    const cleanPrevData = window.EnergyDataUtils.cleanData(prevPeriodData);
    
    if (!cleanCurrentData) {
      console.error("Invalid current period data");
      return null;
    }
    
    // Calculate anomaly scores for production data
    const anomalyScores = window.EnergyDataUtils.calculateAnomalyScores(
      cleanCurrentData.datasets.production
    );
    
    // Create datasets based on options
    const datasets = this.createDatasets(
      cleanCurrentData, 
      cleanPrevData, 
      chartType, 
      options,
      anomalyScores
    );
    
    // Chart configuration with engineering focus
    const chartConfig = this.createChartConfig(chartType, options);
    
    // Create and return the chart
    return new Chart(canvas, {
      type: chartType === 'area' ? 'line' : chartType,
      data: {
        labels: cleanCurrentData.labels,
        datasets: datasets
      },
      options: chartConfig
    });
  },
  
  /**
   * Create datasets for the chart
   * @param {Object} currentData - Current period data
   * @param {Object} prevData - Previous period data
   * @param {String} chartType - Chart type
   * @param {Object} options - Chart options
   * @param {Array} anomalyScores - Anomaly scores for data points
   * @returns {Array} - Datasets for Chart.js
   */
  createDatasets: function(currentData, prevData, chartType, options, anomalyScores) {
    const datasets = [];
    const period = "period"; // This would be determined from context
    
    // Helper function to get label for period
    const getPeriodLabel = (p) => {
      const labels = {
        day: "Day",
        week: "Week",
        month: "Month",
        year: "Year",
        custom: "Period",
        period: "Period"
      };
      return labels[p] || p;
    };
    
    // Current period production
    datasets.push({
      label: `Current ${getPeriodLabel(period)} Production`,
      data: currentData.datasets.production,
      backgroundColor: (ctx) => {
        // Change point color for anomalies
        if (ctx.dataIndex !== undefined && anomalyScores[ctx.dataIndex] > 0.7) {
          return "rgba(239, 68, 68, 0.7)"; // Red for anomalies
        }
        return "rgba(16, 185, 129, 0.7)"; // Default green
      },
      borderColor: (ctx) => {
        if (ctx.dataIndex !== undefined && anomalyScores[ctx.dataIndex] > 0.7) {
          return "rgba(239, 68, 68, 1)"; // Red for anomalies
        }
        return "rgba(16, 185, 129, 1)"; // Default green
      },
      borderWidth: 1,
      borderRadius: chartType === 'bar' ? 4 : 0,
      fill: chartType === 'area',
      tension: 0.3,
      originalId: 'production',
      type: chartType === 'area' ? 'line' : chartType,
      order: 1,
      pointRadius: (ctx) => {
        if (ctx.dataIndex !== undefined && anomalyScores[ctx.dataIndex] > 0.7) {
          return 5; // Larger points for anomalies
        }
        return 3;
      },
      pointStyle: (ctx) => {
        if (ctx.dataIndex !== undefined && anomalyScores[ctx.dataIndex] > 0.7) {
          return 'triangle'; // Different shape for anomalies
        }
        return 'circle';
      }
    });
    
    // Previous period production
    if (prevData && prevData.datasets && prevData.datasets.production) {
      datasets.push({
        label: `Previous ${getPeriodLabel(period)} Production`,
        data: prevData.datasets.production,
        backgroundColor: "rgba(209, 213, 219, 0.5)",
        borderColor: "rgba(209, 213, 219, 0.8)",
        borderWidth: 1,
        borderRadius: chartType === 'bar' ? 4 : 0,
        fill: chartType === 'area',
        tension: 0.3,
        originalId: 'production_prev',
        type: chartType === 'area' ? 'line' : chartType,
        order: 2
      });
    }
    
    // Add consumption data if available
    if (currentData.datasets.consumption) {
      datasets.push({
        label: `Energy Consumption`,
        data: currentData.datasets.consumption,
        backgroundColor: "rgba(79, 70, 229, 0.5)",
        borderColor: "rgba(79, 70, 229, 0.8)",
        borderWidth: 1,
        borderRadius: chartType === 'bar' ? 4 : 0,
        fill: chartType === 'area',
        tension: 0.3,
        originalId: 'consumption',
        type: chartType === 'area' ? 'line' : chartType,
        order: 3,
        hidden: true // Hide by default
      });
    }
    
    // Add grid export/import if available
    if (currentData.datasets.gridExport) {
      datasets.push({
        label: `Grid Export`,
        data: currentData.datasets.gridExport,
        backgroundColor: "rgba(245, 158, 11, 0.5)",
        borderColor: "rgba(245, 158, 11, 0.8)",
        borderWidth: 1,
        borderRadius: chartType === 'bar' ? 4 : 0,
        fill: chartType === 'area',
        tension: 0.3,
        originalId: 'gridExport',
        type: chartType === 'area' ? 'line' : chartType,
        order: 4,
        hidden: true // Hide by default
      });
    }
    
    if (currentData.datasets.gridImport) {
      datasets.push({
        label: `Grid Import`,
        data: currentData.datasets.gridImport,
        backgroundColor: "rgba(220, 38, 38, 0.5)",
        borderColor: "rgba(220, 38, 38, 0.8)",
        borderWidth: 1,
        borderRadius: chartType === 'bar' ? 4 : 0,
        fill: chartType === 'area',
        tension: 0.3,
        originalId: 'gridImport',
        type: chartType === 'area' ? 'line' : chartType,
        order: 5,
        hidden: true // Hide by default
      });
    }
    
    // Add expected production if available and enabled
    if (options && options.showExpectedOutput && currentData.datasets.expectedProduction) {
      datasets.push({
        label: `Expected Production`,
        data: currentData.datasets.expectedProduction,
        backgroundColor: "rgba(16, 185, 129, 0.1)",
        borderColor: "rgba(16, 185, 129, 0.5)",
        borderWidth: 2,
        borderDash: [5, 5],
        fill: false,
        tension: 0.3,
        originalId: 'expectedProduction',
        type: 'line',
        pointRadius: 0,
        order: 6
      });
    }
    
    // Add moving average if enabled
    if (options && options.showMovingAverage && currentData.datasets.production) {
      const movingAvgWindow = options.movingAverageWindow || 5;
      const movingAvgData = window.EnergyDataUtils.calculateMovingAverage(
        currentData.datasets.production, 
        movingAvgWindow
      );
      
      datasets.push({
        label: `${movingAvgWindow}-Period Moving Average`,
        data: movingAvgData,
        backgroundColor: "rgba(6, 95, 70, 0)",
        borderColor: "rgba(6, 95, 70, 1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        originalId: 'movingAverage',
        type: 'line',
        pointRadius: 0,
        order: 0
      });
    }
    
    return datasets;
  },
  
  /**
   * Create chart configuration with engineering focus
   * @param {String} chartType - Chart type
   * @param {Object} options - Chart options
   * @returns {Object} - Chart.js configuration object
   */
  createChartConfig: function(chartType, options) {
    // Default options
    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
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
            label: (context) => {
              const value =
                context.parsed.y !== null
                  ? context.parsed.y.toFixed(2) + " kWh"
                  : "N/A";
              return `${context.dataset.label || ""}: ${value}`;
            },
            // Add footer for anomaly detection
            footer: (tooltipItems) => {
              const datasetIndex = tooltipItems[0].datasetIndex;
              const dataIndex = tooltipItems[0].dataIndex;
              
              if (datasetIndex === 0) { // First dataset (current production)
                const anomalyScore = window.EnergyDataUtils.calculateAnomalyScores(
                  tooltipItems[0].chart.data.datasets[0].data
                )[dataIndex];
                
                if (anomalyScore > 0.7) {
                  return ["Potential anomaly detected"];
                }
              }
              return "";
            }
          },
        },
        datalabels: {
          display: options && options.showDataLabels,
          color: '#374151',
          align: 'top',
          formatter: (value) => value ? value.toFixed(1) : '',
          font: {
            weight: 'bold',
            size: 10
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            color: "rgba(243, 244, 246, 0.8)",
            lineWidth: 1,
            drawBorder: false,
          },
          border: { display: false },
          ticks: {
            padding: 10,
            color: "#6B7280",
            font: { size: 11 },
            callback: (value) => `${value} kWh`
          },
          title: {
            display: true,
            text: "Energy (kWh)",
            color: "#374151",
            font: {
              size: 12,
              weight: "normal",
            },
            padding: { bottom: 10 },
          },
        },
        x: {
          grid: {
            display: false,
            drawBorder: false,
          },
          border: { display: false },
          ticks: {
            padding: 10,
            color: "#6B7280",
            font: { size: 11 },
            maxRotation: 45,
            minRotation: 0,
          },
        },
      },
      animation: {
        duration: 1000,
        easing: "easeOutQuart",
      },
    };
    
    // Add annotations if weather events are enabled
    if (options && options.annotateWeatherEvents) {
      chartOptions.plugins.annotation = {
        annotations: {
          line1: {
            type: 'line',
            yMin: 0,
            yMax: 20,
            xMin: 2,
            xMax: 2,
            borderColor: 'rgba(102, 126, 234, 0.5)',
            borderWidth: 2,
            label: {
              content: 'Rain',
              enabled: true,
              position: 'start',
              backgroundColor: 'rgba(102, 126, 234, 0.7)',
            }
          },
          box1: {
            type: 'box',
            xMin: 10,
            xMax: 14,
            yMin: 0,
            yMax: 100,
            backgroundColor: 'rgba(200, 200, 200, 0.1)',
            borderColor: 'rgba(200, 200, 200, 0.25)',
            borderWidth: 1,
            label: {
              content: 'Cloud Cover',
              enabled: true,
              position: 'center',
              backgroundColor: 'rgba(102, 126, 234, 0.7)',
            }
          }
        }
      };
    }
    
    // Add performance ratio visualization if enabled
    if (options && options.showPerformanceRatio) {
      // This would implement PR visualization
    }
    
    return chartOptions;
  }
};
