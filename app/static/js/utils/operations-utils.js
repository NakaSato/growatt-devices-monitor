/**
 * Operations Utilities Module
 * Provides utility functions for managing system operations and configurations
 */

const OperationsUtils = {
  /**
   * Fetch operations data from the API
   * @returns {Promise<Object>} Operations configuration data
   */
  async fetchOperationsData() {
    try {
      const response = await fetch("/api/operations/data");
      if (!response.ok) {
        throw new Error(`Error fetching operations data: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("Failed to fetch operations data:", error);
      return {
        status: "error",
        message: error.message,
        config: this.getDefaultConfig(),
      };
    }
  },

  /**
   * Save configuration data to the server
   * @param {Object} configData - Configuration data to save
   * @returns {Promise<Object>} Result of the save operation
   */
  async saveConfigData(configData) {
    try {
      const response = await fetch("/api/operations/configuration", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(configData),
      });

      if (!response.ok) {
        throw new Error(`Error saving configuration: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Failed to save configuration:", error);
      return {
        status: "error",
        message: error.message,
      };
    }
  },

  /**
   * Get default configuration in case of API failure
   * @returns {Object} Default configuration object
   */
  getDefaultConfig() {
    return {
      general: {
        systemName: "Growatt Monitoring System",
        defaultView: "dashboard",
        timezone: "UTC",
        refreshRate: 60,
      },
      api: {
        baseUrl: "https://server.growatt.com",
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
    };
  },

  /**
   * Format configuration for display
   * @param {Object} config - Raw configuration object
   * @returns {Object} Formatted configuration object
   */
  formatConfigForDisplay(config) {
    // Make a deep copy to avoid modifying the original
    const formatted = JSON.parse(JSON.stringify(config));

    // Format specific fields as needed
    if (formatted.api && formatted.api.cacheDuration) {
      formatted.api.cacheDuration = parseInt(formatted.api.cacheDuration);
    }

    if (formatted.advanced && formatted.advanced.dataRetention) {
      formatted.advanced.dataRetention = parseInt(
        formatted.advanced.dataRetention
      );
    }

    return formatted;
  },
};

// Export the utilities module
window.OperationsUtils = OperationsUtils;
