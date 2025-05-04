/**
 * Operations App Component for Alpine.js
 * Handles operations management for solar monitoring system
 */

document.addEventListener("alpine:init", () => {
  Alpine.data("operationsApp", () => ({
    // App state
    activeTab: "dashboard",
    isLoading: true,
    hasError: false,
    errorMessage: "",

    // Solar monitoring specific data
    solarData: {
      summary: {
        totalPlants: 0,
        totalDevices: 0,
        totalCapacity: 0,
        activeDevices: 0,
        offlineDevices: 0,
        alertCount: 0,
      },
      production: {
        daily: 0,
        weekly: 0,
        monthly: 0,
        yearly: 0,
        total: 0,
        currentPower: 0,
        peakPower: 0,
      },
      performance: {
        dailyPR: 0,
        monthlyPR: 0,
        yearlyPR: 0,
        specificYield: 0,
        efficiency: 0,
      },
      environmental: {
        co2Avoided: 0,
        treesEquivalent: 0,
        savingsAmount: 0,
      },
      alerts: [],
      maintenance: {
        scheduledTasks: [],
        completedTasks: [],
      },
      monitoring: {
        devices: [],
        dataPoints: [],
      },
    },

    // System configuration
    configSection: "general",
    configData: {
      general: {
        systemName: "Growatt Monitoring System",
        defaultView: "dashboard",
        timezone: "UTC",
        refreshRate: 60,
      },
      api: {
        baseUrl: "https://server.growatt.com/api/",
        timeout: 10,
        rateLimit: 60,
        cacheDuration: 5,
      },
      notifications: {
        enableEmail: false,
        emailAddress: "",
        emailFrequency: "daily",
        enablePush: false,
        notifyAlerts: true,
        notifyPerformance: false,
        notifyMaintenance: true,
      },
      advanced: {
        debugMode: false,
        dbType: "sqlite",
        dbConnection: "",
        dataRetention: 90,
        enableML: true,
      },
      solar: {
        monitoringFrequency: 5,
        performanceRatioThreshold: 75,
        alertThresholds: {
          lowProduction: 70,
          highTemperature: 75,
          lowEfficiency: 80,
        },
        environmentalFactors: {
          co2EmissionFactor: 0.5,
          treesPerTonCO2: 45,
          electricityRate: 0.12,
        },
      },
    },

    // Solar system monitoring scope
    monitoringScope: {
      categories: [
        { id: "inverters", name: "Inverters", enabled: true, devices: 0 },
        { id: "panels", name: "Solar Panels", enabled: true, devices: 0 },
        { id: "batteries", name: "Energy Storage", enabled: false, devices: 0 },
        { id: "meters", name: "Smart Meters", enabled: true, devices: 0 },
        { id: "weather", name: "Weather Stations", enabled: false, devices: 0 },
        { id: "grid", name: "Grid Connection", enabled: true, devices: 0 },
      ],
      parameters: [
        { id: "power", name: "Power Output", enabled: true, unit: "kW" },
        { id: "energy", name: "Energy Production", enabled: true, unit: "kWh" },
        { id: "voltage", name: "Voltage", enabled: true, unit: "V" },
        { id: "current", name: "Current", enabled: true, unit: "A" },
        { id: "temperature", name: "Temperature", enabled: true, unit: "°C" },
        { id: "efficiency", name: "Efficiency", enabled: true, unit: "%" },
        {
          id: "irradiance",
          name: "Solar Irradiance",
          enabled: false,
          unit: "W/m²",
        },
        { id: "battery", name: "Battery Level", enabled: false, unit: "%" },
      ],
      timeframes: [
        { id: "realtime", name: "Real-time", enabled: true },
        { id: "hourly", name: "Hourly", enabled: true },
        { id: "daily", name: "Daily", enabled: true },
        { id: "weekly", name: "Weekly", enabled: true },
        { id: "monthly", name: "Monthly", enabled: true },
        { id: "yearly", name: "Yearly", enabled: true },
      ],
    },

    // Charts
    charts: {},

    // Initialize the component
    init() {
      this.loadData();

      // Set up interval to refresh data
      setInterval(() => {
        if (!this.isLoading) {
          this.refreshData();
        }
      }, 60000); // Refresh every minute
    },

    // Load initial data
    loadData() {
      this.isLoading = true;
      this.hasError = false;

      // Simulate API call to load data
      setTimeout(() => {
        try {
          // In a real app, this would fetch data from an API endpoint
          this.fetchSolarMonitoringData();
          this.fetchSystemConfiguration();
          this.isLoading = false;

          // Initialize charts after data is loaded
          this.$nextTick(() => {
            this.initializeCharts();
          });
        } catch (error) {
          console.error("Error loading data:", error);
          this.hasError = true;
          this.errorMessage = "Failed to load data. Please try again.";
          this.isLoading = false;
        }
      }, 1000);
    },

    // Refresh data
    refreshData() {
      this.isLoading = true;

      // Simulate API call to refresh data
      setTimeout(() => {
        try {
          this.fetchSolarMonitoringData();
          this.isLoading = false;

          // Update charts with new data
          this.$nextTick(() => {
            this.updateCharts();
          });
        } catch (error) {
          console.error("Error refreshing data:", error);
          this.hasError = true;
          this.errorMessage = "Failed to refresh data. Please try again.";
          this.isLoading = false;
        }
      }, 1000);
    },

    // Fetch solar monitoring data
    fetchSolarMonitoringData() {
      // This would be an API call in a real application
      // For now, we'll use simulated data

      this.solarData = {
        summary: {
          totalPlants: 5,
          totalDevices: 32,
          totalCapacity: 250.5, // kWp
          activeDevices: 28,
          offlineDevices: 4,
          alertCount: 3,
        },
        production: {
          daily: 875.2, // kWh
          weekly: 5950.6, // kWh
          monthly: 25480.3, // kWh
          yearly: 290500.8, // kWh
          total: 520450.6, // kWh
          currentPower: 125.4, // kW
          peakPower: 225.8, // kW
        },
        performance: {
          dailyPR: 88.5, // %
          monthlyPR: 86.2, // %
          yearlyPR: 84.7, // %
          specificYield: 4.2, // kWh/kWp
          efficiency: 92.3, // %
        },
        environmental: {
          co2Avoided: 260225.3, // kg
          treesEquivalent: 12050, // trees
          savingsAmount: 62454.07, // $
        },
        alerts: [
          {
            id: 1,
            severity: "high",
            type: "device",
            message: "Inverter offline",
            timestamp: "2025-05-04T08:15:30Z",
            status: "open",
          },
          {
            id: 2,
            severity: "medium",
            type: "performance",
            message: "Low performance ratio",
            timestamp: "2025-05-03T14:22:45Z",
            status: "open",
          },
          {
            id: 3,
            severity: "low",
            type: "monitoring",
            message: "Communication error with weather station",
            timestamp: "2025-05-02T09:45:12Z",
            status: "closed",
          },
        ],
        maintenance: {
          scheduledTasks: [
            {
              id: 1,
              type: "inspection",
              title: "Quarterly panel inspection",
              dueDate: "2025-05-15",
              priority: "medium",
              status: "scheduled",
            },
            {
              id: 2,
              type: "cleaning",
              title: "Panel cleaning",
              dueDate: "2025-05-20",
              priority: "high",
              status: "scheduled",
            },
            {
              id: 3,
              type: "repair",
              title: "Inverter replacement",
              dueDate: "2025-05-10",
              priority: "high",
              status: "in-progress",
            },
          ],
          completedTasks: [
            {
              id: 4,
              type: "inspection",
              title: "Monthly system check",
              completedDate: "2025-04-15",
              findings: "All systems normal",
            },
            {
              id: 5,
              type: "cleaning",
              title: "Panel cleaning",
              completedDate: "2025-04-05",
              findings: "Removed debris, 2% efficiency improvement",
            },
          ],
        },
        monitoring: {
          devices: [
            {
              id: 1,
              type: "inverter",
              name: "Inverter A1",
              status: "online",
              lastUpdate: "2025-05-04T09:55:30Z",
            },
            {
              id: 2,
              type: "inverter",
              name: "Inverter A2",
              status: "online",
              lastUpdate: "2025-05-04T09:55:28Z",
            },
            {
              id: 3,
              type: "inverter",
              name: "Inverter B1",
              status: "offline",
              lastUpdate: "2025-05-04T08:15:30Z",
            },
            {
              id: 4,
              type: "meter",
              name: "Smart Meter 1",
              status: "online",
              lastUpdate: "2025-05-04T09:55:15Z",
            },
          ],
          dataPoints: this.generateSampleDataPoints(),
        },
      };

      // Update monitoring scope counters
      this.updateMonitoringScopeCounters();
    },

    // Fetch system configuration
    fetchSystemConfiguration() {
      // This would be an API call in a real application
      // For now, we'll use the default configuration
    },

    // Initialize charts
    initializeCharts() {
      // Power production chart
      this.charts.powerProduction =
        OperationsUtils.generateSolarProductionChart(
          "power-production-chart",
          this.solarData.monitoring.dataPoints
        );

      // Performance chart (to be implemented)
    },

    // Update charts with new data
    updateCharts() {
      if (this.charts.powerProduction) {
        this.charts.powerProduction.data.datasets[0].data =
          this.solarData.monitoring.dataPoints.map((item) => item.power);
        this.charts.powerProduction.data.datasets[1].data =
          this.solarData.monitoring.dataPoints.map((item) => item.energy);
        this.charts.powerProduction.update();
      }
    },

    // Generate sample data points for demonstration
    generateSampleDataPoints() {
      const dataPoints = [];
      const now = new Date();

      for (let i = 0; i < 24; i++) {
        const timestamp = new Date(now);
        timestamp.setHours(now.getHours() - 23 + i);

        // Simulate solar production pattern (higher during daylight hours)
        const hour = timestamp.getHours();
        let powerFactor = 0;

        // Create a bell curve peaking at noon
        if (hour >= 6 && hour <= 18) {
          powerFactor = 1 - Math.abs(hour - 12) / 6;
        }

        const power = powerFactor * 200 + Math.random() * 20; // kW
        const energy = powerFactor * 180 + Math.random() * 15; // kWh

        dataPoints.push({
          timestamp: timestamp.toISOString(),
          power: power,
          energy: energy,
          temperature: 25 + powerFactor * 15 + Math.random() * 5,
          voltage: 220 + Math.random() * 10,
          current: powerFactor * 50 + Math.random() * 5,
        });
      }

      return dataPoints;
    },

    // Update monitoring scope device counters
    updateMonitoringScopeCounters() {
      // Count devices by type
      const deviceCounts = {
        inverters: 0,
        panels: 0,
        batteries: 0,
        meters: 0,
        weather: 0,
        grid: 0,
      };

      // In a real app, this would use actual device data
      // For demo purposes, we'll set some sample values
      deviceCounts.inverters = 8;
      deviceCounts.panels = 150;
      deviceCounts.batteries = 2;
      deviceCounts.meters = 5;
      deviceCounts.weather = 1;
      deviceCounts.grid = 1;

      // Update the categories with the counts
      this.monitoringScope.categories.forEach((category) => {
        category.devices = deviceCounts[category.id] || 0;
      });
    },

    // Navigate between tabs using keyboard
    navigateTab(direction) {
      const tabs = [
        "dashboard",
        "maintenance",
        "monitoring",
        "performance",
        "alerts",
        "configuration",
      ];
      const currentIndex = tabs.indexOf(this.activeTab);

      if (direction === "next") {
        this.activeTab = tabs[(currentIndex + 1) % tabs.length];
      } else if (direction === "prev") {
        this.activeTab = tabs[(currentIndex - 1 + tabs.length) % tabs.length];
      }
    },

    // Generate operations report
    generateOperationsReport() {
      OperationsUtils.generateOperationsReport();
    },

    // Save configuration changes
    saveConfiguration() {
      this.isLoading = true;

      // Simulate API call to save configuration
      setTimeout(() => {
        this.isLoading = false;
        alert("Configuration saved successfully");
      }, 1000);
    },

    // Reset configuration to defaults
    resetConfiguration() {
      if (
        confirm("Are you sure you want to reset all configuration changes?")
      ) {
        this.fetchSystemConfiguration();
      }
    },

    // Format energy value
    formatEnergy(value) {
      return OperationsUtils.formatEnergyValue(value);
    },

    // Format power value
    formatPower(value) {
      return OperationsUtils.formatPowerValue(value);
    },

    // Get color based on performance
    getPerformanceColor(value) {
      return OperationsUtils.getPerformanceColor(value);
    },
  }));
});
