/**
 * data-formatter.js - Utility functions for formatting data in the Growatt monitoring application
 *
 * This file provides helper functions for formatting various types of data:
 * - Energy values (kWh, MWh)
 * - Power values (W, kW)
 * - Currency values
 * - Dates and times
 * - Percentages
 * - CO2 emission savings
 */

/**
 * Format energy values with appropriate units (Wh, kWh, MWh)
 * @param {number} value - The energy value to format
 * @param {string} unit - Default unit of the input value ('Wh', 'kWh', 'MWh')
 * @param {number} decimals - Number of decimal places to show
 * @param {boolean} includeUnit - Whether to include the unit in the output
 * @returns {string} Formatted energy value
 */
function formatEnergy(value, unit = "kWh", decimals = 2, includeUnit = true) {
  if (value === null || value === undefined || isNaN(value)) {
    return includeUnit ? "0 " + unit : "0";
  }

  // Convert everything to kWh for consistent handling
  let valueInkWh = value;
  if (unit.toLowerCase() === "wh") {
    valueInkWh = value / 1000;
  } else if (unit.toLowerCase() === "mwh") {
    valueInkWh = value * 1000;
  }

  // Format based on value magnitude
  if (valueInkWh >= 1000) {
    // Convert to MWh for large values
    const formattedValue = (valueInkWh / 1000).toFixed(decimals);
    return includeUnit ? `${formattedValue} MWh` : formattedValue;
  } else if (valueInkWh < 0.01) {
    // Show Wh for very small values
    const formattedValue = (valueInkWh * 1000).toFixed(0);
    return includeUnit ? `${formattedValue} Wh` : formattedValue;
  } else {
    // Show kWh for normal values
    const formattedValue = valueInkWh.toFixed(decimals);
    return includeUnit ? `${formattedValue} kWh` : formattedValue;
  }
}

/**
 * Format power values with appropriate units (W, kW)
 * @param {number} value - The power value to format
 * @param {string} unit - Default unit of the input value ('W', 'kW')
 * @param {number} decimals - Number of decimal places to show
 * @param {boolean} includeUnit - Whether to include the unit in the output
 * @returns {string} Formatted power value
 */
function formatPower(value, unit = "W", decimals = 2, includeUnit = true) {
  if (value === null || value === undefined || isNaN(value)) {
    return includeUnit ? "0 " + unit : "0";
  }

  // Convert everything to W for consistent handling
  let valueInW = value;
  if (unit.toLowerCase() === "kw") {
    valueInW = value * 1000;
  }

  // Format based on value magnitude
  if (valueInW >= 1000) {
    // Convert to kW for large values
    const formattedValue = (valueInW / 1000).toFixed(decimals);
    return includeUnit ? `${formattedValue} kW` : formattedValue;
  } else {
    // Show W for small values
    const formattedValue = Math.round(valueInW);
    return includeUnit ? `${formattedValue} W` : formattedValue;
  }
}

/**
 * Format a percentage value
 * @param {number} value - The value to format as a percentage
 * @param {number} decimals - Number of decimal places to show
 * @param {boolean} includeSymbol - Whether to include the % symbol
 * @returns {string} Formatted percentage
 */
function formatPercentage(value, decimals = 1, includeSymbol = true) {
  if (value === null || value === undefined || isNaN(value)) {
    return includeSymbol ? "0%" : "0";
  }

  const formattedValue = value.toFixed(decimals);
  return includeSymbol ? `${formattedValue}%` : formattedValue;
}

/**
 * Format a currency value
 * @param {number} value - The value to format as currency
 * @param {string} currency - Currency code (USD, EUR, THB, etc.)
 * @param {string} locale - Locale for formatting (defaults to browser locale)
 * @returns {string} Formatted currency value
 */
function formatCurrency(value, currency = "USD", locale = undefined) {
  if (value === null || value === undefined || isNaN(value)) {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
    }).format(0);
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a date or datetime value
 * @param {string|Date} dateValue - The date to format
 * @param {string} format - Format type: 'date', 'time', 'datetime', 'relative'
 * @param {string} locale - Locale for formatting (defaults to browser locale)
 * @returns {string} Formatted date string
 */
function formatDate(dateValue, format = "date", locale = undefined) {
  if (!dateValue) return "";

  const date = dateValue instanceof Date ? dateValue : new Date(dateValue);

  if (isNaN(date.getTime())) return "";

  switch (format.toLowerCase()) {
    case "date":
      return date.toLocaleDateString(locale);
    case "time":
      return date.toLocaleTimeString(locale, {
        hour: "2-digit",
        minute: "2-digit",
      });
    case "datetime":
      return date.toLocaleString(locale);
    case "relative":
      return formatRelativeTime(date);
    case "monthday":
      return date.toLocaleDateString(locale, {
        month: "short",
        day: "numeric",
      });
    case "monthyear":
      return date.toLocaleDateString(locale, {
        month: "short",
        year: "numeric",
      });
    case "yearmonth":
      return date.toLocaleDateString(locale, {
        year: "numeric",
        month: "2-digit",
      });
    default:
      return date.toLocaleString(locale);
  }
}

/**
 * Format a date as a relative time string (e.g., "2 hours ago")
 * @param {Date} date - The date to format
 * @returns {string} Relative time string
 */
function formatRelativeTime(date) {
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.round(diffMs / 1000);
  const diffMin = Math.round(diffSec / 60);
  const diffHour = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHour / 24);

  if (diffSec < 60) {
    return "just now";
  } else if (diffMin < 60) {
    return `${diffMin} ${diffMin === 1 ? "minute" : "minutes"} ago`;
  } else if (diffHour < 24) {
    return `${diffHour} ${diffHour === 1 ? "hour" : "hours"} ago`;
  } else if (diffDay < 30) {
    return `${diffDay} ${diffDay === 1 ? "day" : "days"} ago`;
  } else {
    return date.toLocaleDateString();
  }
}

/**
 * Format a temperature value
 * @param {number} value - The temperature value to format
 * @param {string} unit - Temperature unit ('C' or 'F')
 * @param {number} decimals - Number of decimal places to show
 * @param {boolean} includeSymbol - Whether to include the degree symbol
 * @returns {string} Formatted temperature
 */
function formatTemperature(
  value,
  unit = "C",
  decimals = 1,
  includeSymbol = true
) {
  if (value === null || value === undefined || isNaN(value)) {
    return includeSymbol ? `0°${unit}` : "0";
  }

  // Convert if necessary (not implemented, just placeholder)
  let tempValue = value;
  let tempUnit = unit.toUpperCase();

  // Format value
  const formattedValue = tempValue.toFixed(decimals);
  return includeSymbol ? `${formattedValue}°${tempUnit}` : formattedValue;
}

/**
 * Format CO2 emission savings
 * @param {number} value - CO2 savings in kg
 * @param {number} decimals - Number of decimal places to show
 * @param {boolean} includeUnit - Whether to include the unit in the output
 * @returns {string} Formatted CO2 savings
 */
function formatCO2Savings(value, decimals = 2, includeUnit = true) {
  if (value === null || value === undefined || isNaN(value)) {
    return includeUnit ? "0 kg" : "0";
  }

  if (value >= 1000) {
    // Convert to metric tons for large values
    const formattedValue = (value / 1000).toFixed(decimals);
    return includeUnit ? `${formattedValue} tons` : formattedValue;
  } else {
    // Show kg for smaller values
    const formattedValue = value.toFixed(decimals);
    return includeUnit ? `${formattedValue} kg` : formattedValue;
  }
}

/**
 * Format a number with thousand separators
 * @param {number} value - The number to format
 * @param {number} decimals - Number of decimal places
 * @param {string} locale - Locale for formatting (defaults to browser locale)
 * @returns {string} Formatted number
 */
function formatNumber(value, decimals = 2, locale = undefined) {
  if (value === null || value === undefined || isNaN(value)) {
    return "0";
  }

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

// Make functions available globally
window.dataFormatter = {
  formatEnergy,
  formatPower,
  formatPercentage,
  formatCurrency,
  formatDate,
  formatRelativeTime,
  formatTemperature,
  formatCO2Savings,
  formatNumber,
};
