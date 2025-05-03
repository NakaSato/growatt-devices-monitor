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
    if (power >= 1000) {
      return `${(power / 1000).toFixed(2)} MW`;
    }
    return `${power.toFixed(2)} kW`;
  },

  /**
   * Format an energy value with kWh unit
   * @param {number|string} energy - Energy value to format
   * @returns {string} Formatted energy with unit
   */
  formatEnergy(energy) {
    if (energy === undefined || energy === null) return "N/A";
    if (energy >= 1000) {
      return `${(energy / 1000).toFixed(2)} MWh`;
    }
    return `${energy.toFixed(2)} kWh`;
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
      active: "bg-green-50 text-white border border-green-400 shadow-sm",
      inactive:
        "bg-gradient-to-r from-gray-400 to-gray-500 text-white border border-gray-600 shadow-sm",
      maintenance:
        "bg-gradient-to-r from-amber-400 to-amber-500 text-amber-900 border border-amber-600 shadow-sm",
      error:
        "bg-gradient-to-r from-red-500 to-red-600 text-white border border-red-700 shadow-sm",
      warning:
        "bg-gradient-to-r from-yellow-400 to-yellow-500 text-yellow-900 border border-yellow-600 shadow-sm",
    };
    return (
      classMap[status] ||
      "bg-gradient-to-r from-gray-400 to-gray-500 text-white border border-gray-600 shadow-sm"
    );
  },

  /**
   * Calculate efficiency percentage
   * @param {number} actual - Actual production
   * @param {number} expected - Expected production
   * @returns {string} Formatted efficiency percentage
   */
  calculateEfficiency(actual, expected) {
    if (!expected || expected === 0) return "N/A";
    const efficiency = (actual / expected) * 100;
    return `${efficiency.toFixed(1)}%`;
  },
};

// Make available globally
window.PlantDataUtils = PlantDataUtils;
