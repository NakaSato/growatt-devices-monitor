/**
 * Utility functions for exporting data
 */
const ExportUtils = {
  /**
   * Export data to JSON file
   * @param {Object} data - Data to export
   * @param {string} filename - Name for the exported file
   */
  exportToJSON(data, filename = "export.json") {
    const dataStr = JSON.stringify(data, null, 2);
    this._downloadFile(dataStr, filename, "application/json");
  },

  /**
   * Export data to CSV file
   * @param {Array} data - Array of objects to export as CSV
   * @param {string} filename - Name for the exported file
   */
  exportToCSV(data, filename = "export.csv") {
    if (!data || !data.length) return;

    // Get headers from the first item
    const headers = Object.keys(data[0]);

    // Create CSV rows
    const csvRows = [
      headers.join(","), // Header row
      ...data.map((row) =>
        headers
          .map((field) => {
            // Handle special characters in CSV
            const value = row[field] !== null ? row[field] : "";
            return typeof value === "string"
              ? `"${value.replace(/"/g, '""')}"`
              : value;
          })
          .join(",")
      ),
    ];

    const csvString = csvRows.join("\n");
    this._downloadFile(csvString, filename, "text/csv");
  },

  /**
   * Helper method to trigger file download
   * @private
   */
  _downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.setAttribute("href", url);
    a.setAttribute("download", filename);
    a.style.display = "none";

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Clean up
    URL.revokeObjectURL(url);
  },
};

// Make available globally
window.ExportUtils = ExportUtils;
