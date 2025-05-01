/**
 * Export Utilities
 * Utility functions for data export
 */

const ExportUtils = {
  /**
   * Export data to CSV/Excel file
   * @param {Array} data - Array of objects to export
   * @param {Array} headers - Array of column headers
   * @param {function} rowFormatter - Function to format a row of data
   * @param {string} filenamePrefix - Prefix for the generated filename
   * @param {HTMLElement} buttonElement - Button element to show loading state
   * @param {function} errorCallback - Function to call on error
   */
  exportToCsv(
    data,
    headers,
    rowFormatter,
    filenamePrefix,
    buttonElement,
    errorCallback
  ) {
    if (!data || data.length === 0) {
      if (errorCallback) errorCallback("No data to export.");
      return;
    }

    // Get current date and time for filename and header
    const now = new Date();
    const exportTime = now.toLocaleString();
    const timestamp = now.toISOString().replace(/[:.]/g, "-").substring(0, 19);
    const filename = `${filenamePrefix}_${timestamp}.csv`;

    // Show visual feedback when exporting
    let originalButtonHtml = "";
    if (buttonElement) {
      originalButtonHtml = buttonElement.innerHTML;
      buttonElement.innerHTML =
        '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg><span>Exporting...</span>';
      buttonElement.disabled = true;
    }

    try {
      // Create CSV content with BOM for UTF-8 (helps Excel recognize UTF-8)
      let csvContent = "\uFEFF";

      // Add header information with export time
      csvContent += `"Export - ${exportTime}"\n`;
      csvContent += `"Export Time: ${exportTime}"\n`;
      csvContent += `"Total Items: ${data.length}"\n\n`;

      // Add data table headers
      csvContent += headers.map((header) => `"${header}"`).join(",") + "\n";

      // Add data rows
      data.forEach((item) => {
        const row = rowFormatter(item);
        csvContent += row + "\n";
      });

      // Create download link with proper encoding
      const blob = new Blob([csvContent], {
        type: "text/csv;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", filename);
      document.body.appendChild(link);

      // Trigger download and clean up
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error exporting to CSV:", error);
      if (errorCallback) errorCallback(`Failed to export: ${error.message}`);
    } finally {
      // Restore button state
      if (buttonElement) {
        buttonElement.innerHTML = originalButtonHtml;
        buttonElement.disabled = false;
      }
    }
  },
};

// Make available globally
window.ExportUtils = ExportUtils;
