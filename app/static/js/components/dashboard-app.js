/**
 * Dashboard App Component
 * Alpine.js component for the main dashboard interface
 */
document.addEventListener("alpine:init", () => {
  Alpine.data("dashboardApp", () => ({
    // Dashboard state
    isLoading: true,
    hasError: false,
    errorMessage: "",
    lastUpdated: null,
    refreshInterval: 300000, // 5 minutes
    isRefreshing: false,

    // Dashboard data
    summary: {
      totalPlants: 0,
      activePlants: 0,
      totalPower: 0,
      todayEnergy: 0,
      monthEnergy: 0,
      totalEnergy: 0,
      co2Saved: 0,
      revenue: 0,
    },

    // Charts data
    energyChartData: null,
    powerChartData: null,
    performanceChartData: null,
    deviceStatusChartData: null,

    // Chart instances
    energyChart: null,
    powerChart: null,
    performanceChart: null,
    deviceStatusChart: null,

    // Device data
    devices: [],
    filteredDevices: [],
    deviceTypes: [],
    deviceStatusCount: {
      online: 0,
      offline: 0,
      warning: 0,
      error: 0,
    },

    // Weather data
    weather: null,
    hasWeatherData: false,

    // Alerts & notifications
    alerts: [],
    showNotifications: false,
    unreadAlerts: 0,

    // Filter settings
    timeRange: "today",
    deviceTypeFilter: "all",
    deviceStatusFilter: "all",

    // Component initialization
    init() {
      this.setupResponsiveLayout();
      this.loadDashboardData();
      this.setupPeriodicRefresh();
      this.setupEventListeners();
    },

    // Load all dashboard data
    loadDashboardData() {
      this.isLoading = true;
      this.hasError = false;

      // Use Promise.all to load data in parallel
      Promise.all([
        this.loadSummaryData(),
        this.loadDevicesData(),
        this.loadChartData(),
        this.loadWeatherData(),
        this.loadAlertsData(),
      ])
        .then(() => {
          this.isLoading = false;
          this.lastUpdated = new Date();
          this.renderCharts();
        })
        .catch((error) => {
          console.error("Error loading dashboard data:", error);
          this.hasError = true;
          this.errorMessage = error.message || "Failed to load dashboard data";
          this.isLoading = false;
        });
    },

    // Load summary metrics
    loadSummaryData() {
      return fetch("/api/dashboard/summary")
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          this.summary = {
            totalPlants: data.totalPlants || 0,
            activePlants: data.activePlants || 0,
            totalPower: data.totalPower || 0,
            todayEnergy: data.todayEnergy || 0,
            monthEnergy: data.monthEnergy || 0,
            totalEnergy: data.totalEnergy || 0,
            co2Saved: data.co2Saved || 0,
            revenue: data.revenue || 0,
          };
        });
    },

    // Load devices data
    loadDevicesData() {
      return fetch("/api/devices")
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          this.devices = data || [];
          this.filteredDevices = [...this.devices];

          // Extract device types
          this.deviceTypes = [
            ...new Set(this.devices.map((device) => device.deviceType)),
          ];

          // Count device statuses
          this.countDeviceStatuses();
        });
    },

    // Load chart data based on time range
    loadChartData() {
      return fetch(`/api/dashboard/charts?timeRange=${this.timeRange}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          this.energyChartData = data.energy || null;
          this.powerChartData = data.power || null;
          this.performanceChartData = data.performance || null;
          this.deviceStatusChartData = data.deviceStatus || null;
        });
    },

    // Load weather data
    loadWeatherData() {
      return fetch("/api/weather")
        .then((response) => {
          if (!response.ok) {
            this.hasWeatherData = false;
            // Not treating this as an error
            return null;
          }
          return response.json();
        })
        .then((data) => {
          if (data) {
            this.weather = data;
            this.hasWeatherData = true;
          } else {
            this.hasWeatherData = false;
          }
        })
        .catch(() => {
          this.hasWeatherData = false;
          // Not treating this as an error
        });
    },

    // Load alerts and notifications
    loadAlertsData() {
      return fetch("/api/alerts")
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          this.alerts = data || [];
          this.unreadAlerts = this.alerts.filter((alert) => !alert.read).length;
        });
    },

    // Count device statuses
    countDeviceStatuses() {
      this.deviceStatusCount = {
        online: this.devices.filter((device) => device.status === "online")
          .length,
        offline: this.devices.filter((device) => device.status === "offline")
          .length,
        warning: this.devices.filter((device) => device.status === "warning")
          .length,
        error: this.devices.filter((device) => device.status === "error")
          .length,
      };
    },

    // Render all charts
    renderCharts() {
      this.renderEnergyChart();
      this.renderPowerChart();
      this.renderPerformanceChart();
      this.renderDeviceStatusChart();
    },

    // Energy production chart
    renderEnergyChart() {
      if (!this.energyChartData || !document.getElementById("energy-chart")) {
        return;
      }

      // Destroy existing chart if it exists
      if (this.energyChart) {
        this.energyChart.destroy();
      }

      const ctx = document.getElementById("energy-chart").getContext("2d");
      this.energyChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: this.energyChartData.labels,
          datasets: [
            {
              label: "Energy Production (kWh)",
              data: this.energyChartData.values,
              backgroundColor: "rgba(75, 192, 192, 0.6)",
              borderColor: "rgba(75, 192, 192, 1)",
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: "Energy (kWh)",
              },
            },
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: function (context) {
                  return `Energy: ${context.raw.toFixed(2)} kWh`;
                },
              },
            },
          },
        },
      });
    },

    // Power production chart
    renderPowerChart() {
      if (!this.powerChartData || !document.getElementById("power-chart")) {
        return;
      }

      // Destroy existing chart if it exists
      if (this.powerChart) {
        this.powerChart.destroy();
      }

      const ctx = document.getElementById("power-chart").getContext("2d");
      this.powerChart = new Chart(ctx, {
        type: "line",
        data: {
          labels: this.powerChartData.labels,
          datasets: [
            {
              label: "Power Output (kW)",
              data: this.powerChartData.values,
              fill: false,
              borderColor: "rgba(255, 159, 64, 1)",
              tension: 0.1,
              pointRadius: 2,
              pointHoverRadius: 5,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: "Power (kW)",
              },
            },
          },
        },
      });
    },

    // Performance comparison chart
    renderPerformanceChart() {
      if (
        !this.performanceChartData ||
        !document.getElementById("performance-chart")
      ) {
        return;
      }

      // Destroy existing chart if it exists
      if (this.performanceChart) {
        this.performanceChart.destroy();
      }

      const ctx = document.getElementById("performance-chart").getContext("2d");
      this.performanceChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: this.performanceChartData.labels,
          datasets: [
            {
              label: "Actual",
              data: this.performanceChartData.actual,
              backgroundColor: "rgba(54, 162, 235, 0.6)",
              borderColor: "rgba(54, 162, 235, 1)",
              borderWidth: 1,
            },
            {
              label: "Expected",
              data: this.performanceChartData.expected,
              backgroundColor: "rgba(255, 206, 86, 0.6)",
              borderColor: "rgba(255, 206, 86, 1)",
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: "Energy (kWh)",
              },
            },
          },
        },
      });
    },

    // Device status donut chart
    renderDeviceStatusChart() {
      if (
        !this.deviceStatusCount ||
        !document.getElementById("device-status-chart")
      ) {
        return;
      }

      // Destroy existing chart if it exists
      if (this.deviceStatusChart) {
        this.deviceStatusChart.destroy();
      }

      const ctx = document
        .getElementById("device-status-chart")
        .getContext("2d");
      this.deviceStatusChart = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: ["Online", "Offline", "Warning", "Error"],
          datasets: [
            {
              data: [
                this.deviceStatusCount.online,
                this.deviceStatusCount.offline,
                this.deviceStatusCount.warning,
                this.deviceStatusCount.error,
              ],
              backgroundColor: [
                "rgba(75, 192, 192, 0.6)",
                "rgba(201, 203, 207, 0.6)",
                "rgba(255, 159, 64, 0.6)",
                "rgba(255, 99, 132, 0.6)",
              ],
              borderColor: [
                "rgba(75, 192, 192, 1)",
                "rgba(201, 203, 207, 1)",
                "rgba(255, 159, 64, 1)",
                "rgba(255, 99, 132, 1)",
              ],
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "bottom",
            },
          },
        },
      });
    },

    // Filter devices based on selected filters
    filterDevices() {
      this.filteredDevices = this.devices.filter((device) => {
        const matchesType =
          this.deviceTypeFilter === "all" ||
          device.deviceType === this.deviceTypeFilter;
        const matchesStatus =
          this.deviceStatusFilter === "all" ||
          device.status === this.deviceStatusFilter;
        return matchesType && matchesStatus;
      });
    },

    // Change time range and refresh data
    changeTimeRange(range) {
      this.timeRange = range;
      this.loadChartData().then(() => {
        this.renderCharts();
      });
    },

    // Refresh dashboard data
    refreshData(silent = false) {
      if (!silent) {
        this.isRefreshing = true;
      }

      this.loadDashboardData()
        .then(() => {
          if (!silent) {
            this.showToast("Dashboard data refreshed");
          }
        })
        .catch((error) => {
          console.error("Error refreshing data:", error);
          if (!silent) {
            this.showToast("Failed to refresh data", "error");
          }
        })
        .finally(() => {
          this.isRefreshing = false;
        });
    },

    // Set up periodic refresh
    setupPeriodicRefresh() {
      setInterval(() => {
        // Only refresh if page is visible
        if (!document.hidden) {
          this.refreshData(true);
        }
      }, this.refreshInterval);

      // Refresh when tab becomes visible if enough time has passed
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden && this.lastUpdated) {
          const timeSinceLastUpdate = new Date() - this.lastUpdated;
          if (timeSinceLastUpdate > 60000) {
            // 1 minute
            this.refreshData(true);
          }
        }
      });
    },

    // Set up responsive layout and event listeners
    setupResponsiveLayout() {
      const updateLayout = () => {
        const isMobile = window.innerWidth < 768;
        // Adjust chart sizes or configurations based on screen size
        if (this.energyChart) {
          this.energyChart.options.plugins.legend.display = !isMobile;
          this.energyChart.update();
        }
      };

      // Initial setup
      updateLayout();

      // Update on resize
      window.addEventListener("resize", () => {
        updateLayout();
      });
    },

    // Set up miscellaneous event listeners
    setupEventListeners() {
      // Listen for custom events from components
      document.addEventListener("device-status-changed", () => {
        this.loadDevicesData().then(() => {
          this.renderDeviceStatusChart();
        });
      });

      // Listen for theme changes
      document.addEventListener("theme-changed", () => {
        // Re-render charts with new theme colors
        this.renderCharts();
      });
    },

    // Mark all alerts as read
    markAllAlertsAsRead() {
      fetch("/api/alerts/mark-all-read", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then(() => {
          this.alerts.forEach((alert) => {
            alert.read = true;
          });
          this.unreadAlerts = 0;
          this.showToast("All notifications marked as read");
        })
        .catch((error) => {
          console.error("Error marking alerts as read:", error);
          this.showToast("Failed to update notifications", "error");
        });
    },

    // Toggle alerts panel
    toggleAlerts() {
      this.showNotifications = !this.showNotifications;
    },

    // Format values using the data formatter
    formatEnergy(value, unit = "kWh") {
      return window.dataFormatter
        ? window.dataFormatter.formatEnergy(value, unit)
        : `${value} ${unit}`;
    },

    formatPower(value, unit = "kW") {
      return window.dataFormatter
        ? window.dataFormatter.formatPower(value, unit)
        : `${value} ${unit}`;
    },

    formatCO2(value) {
      return window.dataFormatter
        ? window.dataFormatter.formatCO2Savings(value)
        : `${value} kg`;
    },

    formatCurrency(value, currency = "USD") {
      return window.dataFormatter
        ? window.dataFormatter.formatCurrency(value, currency)
        : `$${value}`;
    },

    formatDate(value, format = "datetime") {
      return window.dataFormatter
        ? window.dataFormatter.formatDate(value, format)
        : value;
    },

    // Show toast messages
    showToast(message, type = "success") {
      if (typeof window.showToast === "function") {
        window.showToast(message, type);
      } else {
        console.log(`Toast (${type}): ${message}`);
        // Fallback if toast utility isn't available
        alert(`${type.charAt(0).toUpperCase() + type.slice(1)}: ${message}`);
      }
    },

    // Export dashboard data
    exportDashboardData() {
      // Show export in progress message
      this.showToast("Preparing export...");

      fetch(`/api/dashboard/export?timeRange=${this.timeRange}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.blob();
        })
        .then((blob) => {
          // Generate filename with current date
          const date = new Date().toISOString().split("T")[0];
          const filename = `growatt_dashboard_${date}.xlsx`;

          // Create download link
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.style.display = "none";
          a.href = url;
          a.download = filename;

          // Trigger download
          document.body.appendChild(a);
          a.click();

          // Clean up
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);

          this.showToast("Export completed successfully");
        })
        .catch((error) => {
          console.error("Error exporting dashboard data:", error);
          this.showToast("Failed to export dashboard data", "error");
        });
    },

    // Get device status CSS class
    getStatusClass(status) {
      const classMap = {
        online: "bg-green-500",
        offline: "bg-gray-500",
        warning: "bg-yellow-500",
        error: "bg-red-500",
      };

      return classMap[status] || "bg-gray-500";
    },

    // Get formatted status text
    getStatusText(status) {
      const textMap = {
        online: "Online",
        offline: "Offline",
        warning: "Warning",
        error: "Error",
      };

      return textMap[status] || "Unknown";
    },

    // Get weather icon class based on weather condition
    getWeatherIconClass(condition) {
      if (!condition) return "fa-sun";

      const lowerCondition = condition.toLowerCase();

      if (
        lowerCondition.includes("clear") ||
        lowerCondition.includes("sunny")
      ) {
        return "fa-sun";
      } else if (lowerCondition.includes("cloud")) {
        return "fa-cloud";
      } else if (
        lowerCondition.includes("rain") ||
        lowerCondition.includes("drizzle")
      ) {
        return "fa-cloud-rain";
      } else if (
        lowerCondition.includes("thunder") ||
        lowerCondition.includes("storm")
      ) {
        return "fa-cloud-bolt";
      } else if (lowerCondition.includes("snow")) {
        return "fa-snowflake";
      } else if (
        lowerCondition.includes("fog") ||
        lowerCondition.includes("mist")
      ) {
        return "fa-smog";
      } else {
        return "fa-cloud-sun";
      }
    },
  }));
});
