/**
 * Alpine.js component for the Management page
 * Controls tab navigation and data loading
 */
function managementApp() {
  return {
    activeTab: "overview",
    isLoading: true,
    hasError: false,
    errorMessage: "",
    systemData: null,

    init() {
      // Load initial data when component is initialized
      this.refreshData();
    },

    refreshData() {
      this.isLoading = true;
      this.hasError = false;

      // Use the new apiCache system
      const apiUrl = "/api/management/data";

      // Configure cache options
      const options = {
        cacheDuration: 5 * 60 * 1000, // 5 minutes cache
        bypassBrowserCache: true,
        requestOptions: {
          headers: {
            "Cache-Control": "no-cache",
          },
        },
      };

      // Use the new cache system
      window.apiCache
        .fetch(apiUrl, options)
        .then((data) => {
          this.systemData = data;
          this.isLoading = false;
        })
        .catch((error) => {
          console.error("Error fetching data:", error);
          this.errorMessage = "Failed to load data. Please try again.";
          this.hasError = true;
          this.isLoading = false;
        });
    },

    exportCurrentData() {
      // Export currently displayed data based on active tab
      const fileName = `growatt-${this.activeTab}-export-${
        new Date().toISOString().split("T")[0]
      }.json`;

      // Create exportable data based on active tab
      let exportData;
      switch (this.activeTab) {
        case "overview":
          exportData = this.systemData?.overview || {};
          break;
        case "plants":
          exportData = this.systemData?.plants || [];
          break;
        case "devices":
          exportData = this.systemData?.devices || [];
          break;
        case "data":
          exportData = this.systemData?.analytics || {};
          break;
        case "health":
          exportData = this.systemData?.health || {};
          break;
        case "settings":
          exportData = this.systemData?.settings || {};
          break;
        default:
          exportData = this.systemData || {};
      }

      // Use the browser's download capabilities
      const dataStr = JSON.stringify(exportData, null, 2);
      const dataBlob = new Blob([dataStr], { type: "application/json" });
      const url = URL.createObjectURL(dataBlob);

      const a = document.createElement("a");
      a.setAttribute("href", url);
      a.setAttribute("download", fileName);
      a.click();

      // Clean up
      URL.revokeObjectURL(url);
    },
  };
}
