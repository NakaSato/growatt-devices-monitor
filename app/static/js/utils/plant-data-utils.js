/**
 * Plant Data Utilities
 * Utility functions for plant data formatting and manipulation
 */

const PlantDataUtils = {
  /**
   * Format a power value with kW unit
   * @param {number|string} power - Power value to format
   * @returns {string} Formatted power with unit
   */
  formatPower(power) {
    if (power === undefined || power === null) return "N/A";
    return `${power} kW`;
  },

  /**
   * Format an energy value with kWh unit
   * @param {number|string} energy - Energy value to format
   * @returns {string} Formatted energy with unit
   */
  formatEnergy(energy) {
    if (energy === undefined || energy === null) return "N/A";
    return `${energy} kWh`;
  },

  /**
   * Format a timezone value to display format
   * @param {number|string} timezone - Timezone value to format
   * @returns {string} Formatted timezone string
   */
  formatTimezone(timezone) {
    if (timezone === undefined || timezone === null) return "N/A";

    // Convert timezone string to number
    const timezoneNum = parseInt(timezone);
    if (isNaN(timezoneNum)) return timezone;

    // Format timezone as UTC+X or UTC-X
    const sign = timezoneNum >= 0 ? "+" : "-";
    const absValue = Math.abs(timezoneNum);
    return `UTC${sign}${absValue}`;
  },

  /**
   * Get the text representation of a plant status
   * @param {string} status - Status code
   * @returns {string} Human-readable status text
   */
  getStatusText(status) {
    const statusMap = {
      active: "Active",
      inactive: "Inactive",
      maintenance: "Maintenance",
      error: "Error",
    };
    return statusMap[status] || "Unknown";
  },

  /**
   * Get the CSS class for a plant status
   * @param {string} status - Status code
   * @returns {string} CSS class for the status
   */
  getStatusClass(status) {
    const classMap = {
      active: "status-active",
      inactive: "status-inactive",
      maintenance: "status-maintenance",
      error: "status-error",
    };
    return classMap[status] || "status-inactive";
  },

  /**
   * Get the badge CSS class for a plant status
   * @param {string} status - Status code
   * @returns {string} Badge CSS class for the status
   */
  getStatusBadgeClass(status) {
    const classMap = {
      active: "bg-green-600",
      inactive: "bg-gray-500",
      maintenance: "bg-amber-500",
      error: "bg-red-600",
    };
    return classMap[status] || "bg-gray-500";
  },
};

// Make available globally
window.PlantDataUtils = PlantDataUtils;
