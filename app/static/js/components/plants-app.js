/**
 * Plants App Component
 * Alpine.js component for managing plant data
 */
document.addEventListener("alpine:init", () => {
  Alpine.data("plantsApp", () => ({
    plants: [],
    filteredPlants: [],
    isLoading: true,
    errorMessage: "",
    lastFetchTime: null,
    cacheDuration: 60000, // Cache duration in milliseconds (1 minute)
    isRefreshing: false, // Track when refreshing data
    viewMode: window.innerWidth < 640 ? "cards" : "table", // Default to cards on smaller screens, table on larger ones
    searchQuery: "",
    statusFilter: "all",
    sortField: "plantName", // Default sort field
    sortAsc: true, // Default sort direction
    fetchRetryCount: 0,
    maxRetries: 3,
    retryDelay: 2000, // Initial retry delay in milliseconds

    // Loading status tracking
    loadingStage: "initializing", // 'initializing', 'fetching', 'processing', 'rendering'
    loadingProgress: {
      initializing: true,
      fetching: false,
      processing: false,
      rendering: false,
    },

    // Plant details properties
    selectedPlant: null,
    plantDetails: {},
    paginatedPlantDetails: {},
    showPlantDetailModal: false,
    isLoadingDetails: false,
    detailsCurrentPage: 1,
    detailsTotalPages: 1,
    detailsPerPage: 10,

    // Pagination settings
    currentPage: 1,
    itemsPerPage: 12, // Default number of cards per page
    pageSize: window.innerWidth < 640 ? 6 : 10, // For table view
    visiblePages: 5, // Number of page numbers to show in pagination

    // Compute the total number of pages for current view mode
    get totalPages() {
      if (this.viewMode === "cards") {
        return Math.ceil(this.filteredPlants.length / this.itemsPerPage);
      } else {
        return Math.ceil(this.filteredPlants.length / this.pageSize);
      }
    },

    // Compute paginated plants based on current view mode
    get paginatedPlants() {
      let pageSize =
        this.viewMode === "cards" ? this.itemsPerPage : this.pageSize;
      const start = (this.currentPage - 1) * pageSize;
      const end = start + pageSize;
      return this.filteredPlants.slice(start, end);
    },

    // Calculate visible page numbers for pagination controls
    get visiblePageNumbers() {
      const totalPages = this.totalPages;

      if (totalPages <= this.visiblePages) {
        return Array.from({ length: totalPages }, (_, i) => i + 1);
      }

      let startPage = Math.max(
        this.currentPage - Math.floor(this.visiblePages / 2),
        1
      );
      let endPage = startPage + this.visiblePages - 1;

      if (endPage > totalPages) {
        endPage = totalPages;
        startPage = Math.max(endPage - this.visiblePages + 1, 1);
      }

      return Array.from(
        { length: endPage - startPage + 1 },
        (_, i) => startPage + i
      );
    },

    // Initialize component with responsive settings and user preferences
    init() {
      // Load user preference for items per page
      const savedItemsPerPage = localStorage.getItem("preferredItemsPerPage");
      if (savedItemsPerPage) {
        this.itemsPerPage = parseInt(savedItemsPerPage);
      } else {
        // Set default based on screen size
        this.itemsPerPage = window.innerWidth < 768 ? 8 : 12;
      }

      // Responsive view mode toggle based on screen size
      window.addEventListener("resize", () => {
        // Only auto-switch view mode if the user hasn't manually selected one
        if (!localStorage.getItem("preferredViewMode")) {
          this.viewMode = window.innerWidth < 640 ? "cards" : "table";
        }

        // Update page sizes when screen size changes
        if (window.innerWidth < 640) {
          this.pageSize = 6;
          if (!localStorage.getItem("preferredItemsPerPage")) {
            this.itemsPerPage = 8;
          }
        } else if (window.innerWidth < 1024) {
          this.pageSize = 10;
          if (!localStorage.getItem("preferredItemsPerPage")) {
            this.itemsPerPage = 12;
          }
        } else {
          this.pageSize = 10;
          if (!localStorage.getItem("preferredItemsPerPage")) {
            this.itemsPerPage = 16;
          }
        }

        // Ensure pagination is updated
        this.updatePagination();
      });

      // Check for saved preferences
      const savedViewMode = localStorage.getItem("preferredViewMode");
      if (savedViewMode) {
        this.viewMode = savedViewMode;
      }

      // Check for cached data
      const cachedPlants = this.getCachedPlants();
      if (cachedPlants) {
        this.plants = cachedPlants;
        this.filteredPlants = [...this.plants];
        this.sortPlants();
        this.isLoading = false;

        // Fetch fresh data in the background after rendering cached data
        setTimeout(() => this.fetchPlants(true), 100);
      } else {
        this.fetchPlants();
      }

      // Set up a periodic refresh if the tab is visible
      this.setupPeriodicRefresh();
    },

    // Setup periodic refresh of plant data
    setupPeriodicRefresh() {
      // Default refresh interval in milliseconds (5 minutes)
      const refreshInterval = 300000;

      // Function to check if page is visible and refresh data if needed
      const checkVisibilityAndRefresh = () => {
        // Only refresh if the page is visible to the user
        if (!document.hidden) {
          // Check if it's time to refresh (based on last fetch time)
          const timeSinceLastFetch = Date.now() - (this.lastFetchTime || 0);
          if (timeSinceLastFetch >= refreshInterval) {
            console.log("Performing periodic background refresh");
            this.fetchPlants(true); // Silent refresh
          }
        }
      };

      // Set up periodic check
      setInterval(checkVisibilityAndRefresh, 60000); // Check every minute

      // Also refresh when user returns to the page
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
          const timeSinceLastFetch = Date.now() - (this.lastFetchTime || 0);
          // Only refresh if it's been at least 1 minute since the last fetch
          if (timeSinceLastFetch >= 60000) {
            console.log("Page became visible, refreshing data");
            this.fetchPlants(true); // Silent refresh
          }
        }
      });
    },

    // Updated pagination methods with better navigation
    updatePagination() {
      // Make sure current page is valid after filtering or changing items per page
      if (this.currentPage > this.totalPages && this.totalPages > 0) {
        this.currentPage = this.totalPages;
      } else if (this.currentPage < 1) {
        this.currentPage = 1;
      }

      // Save preference for items per page
      localStorage.setItem(
        "preferredItemsPerPage",
        this.itemsPerPage.toString()
      );
    },

    prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--;
      }
    },

    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
      }
    },

    goToPage(page) {
      if (page >= 1 && page <= this.totalPages) {
        this.currentPage = page;
      }
    },

    goToFirstPage() {
      this.currentPage = 1;
    },

    goToLastPage() {
      this.currentPage = this.totalPages;
    },

    // Apply filtering and ensure pagination is updated
    filterPlants() {
      // Store current page before filtering
      const previousPage = this.currentPage;

      // Filter by search query and status
      this.filteredPlants = this.plants.filter((plant) => {
        const matchesSearch =
          !this.searchQuery ||
          (plant.plantName &&
            plant.plantName
              .toLowerCase()
              .includes(this.searchQuery.toLowerCase())) ||
          (plant.id && plant.id.toString().includes(this.searchQuery)) ||
          (plant.location &&
            plant.location
              .toLowerCase()
              .includes(this.searchQuery.toLowerCase()));

        const matchesStatus =
          this.statusFilter === "all" ||
          (plant.status || "active") === this.statusFilter;

        return matchesSearch && matchesStatus;
      });

      // Apply current sorting
      this.sortPlants();

      // Reset to first page when filtering changes results
      if (
        this.filteredPlants.length === 0 ||
        (previousPage > this.totalPages && this.totalPages > 0)
      ) {
        this.currentPage = 1;
      }
    },

    // Cache plants data
    cachePlants(plants) {
      const timestamp = Date.now();
      this.lastFetchTime = timestamp;

      try {
        localStorage.setItem(
          "plantsCache",
          JSON.stringify({
            timestamp,
            plants,
          })
        );
      } catch (e) {
        console.error("Error caching plants data:", e);
      }
    },

    // Get cached plants data
    getCachedPlants() {
      try {
        const cachedData = localStorage.getItem("plantsCache");
        if (!cachedData) return null;

        const { timestamp, plants } = JSON.parse(cachedData);

        // Check if cache has expired
        if (Date.now() - timestamp > this.cacheDuration) {
          console.log("Cache expired, fetching fresh data");
          return null;
        }

        return plants;
      } catch (e) {
        console.error("Error retrieving cached plants data:", e);
        return null;
      }
    },

    fetchPlants(silentRefresh = false) {
      if (!silentRefresh) {
        this.isLoading = true;
      } else {
        this.isRefreshing = true;
      }

      this.hasError = false;

      // Use the new apiCache system
      const apiUrl = "/api/plants";

      // Set up fetch options
      const options = {
        forceFresh: silentRefresh, // Force fresh data on manual refresh
        cacheDuration: this.cacheDuration,
        bypassBrowserCache: true,
        requestOptions: {
          method: "GET",
          headers: {
            "Cache-Control": "no-cache",
          },
          credentials: "same-origin",
        },
      };

      // Use the cache system
      window.apiCache
        .fetch(apiUrl, options)
        .then((data) => {
          // Data processing on success
          if (Array.isArray(data)) {
            this.plants = data;
            this.filteredPlants = [...this.plants];
            this.sortPlants();
            this.updatePagination();
          } else {
            throw new Error("Invalid data format received from API");
          }

          // Reset loading states
          this.isLoading = false;
          this.isRefreshing = false;
        })
        .catch((error) => {
          console.error("Error fetching plants data:", error);
          this.hasError = true;
          this.errorMessage = error.message || "Failed to load plants data";

          // Reset loading states
          this.isLoading = false;
          this.isRefreshing = false;
        });
    },

    // Fetch a single plant by ID
    fetchSinglePlant(plantId) {
      // Show loading state for this plant
      const plantIndex = this.plants.findIndex((p) => p.id == plantId);
      if (plantIndex === -1) return;

      // Set loading state for this plant
      this.plants[plantIndex].isRefreshing = true;

      // Create a copy of the original plant for restoring if needed
      const originalPlant = { ...this.plants[plantIndex] };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

      fetch(`/api/plants/${plantId}`, {
        signal: controller.signal,
        headers: {
          "Cache-Control": "no-cache",
          Pragma: "no-cache",
        },
      })
        .then((response) => {
          clearTimeout(timeoutId);
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          // Log the received data to console
          console.log(`Received data for plant ${plantId}:`, data);

          // Process the plant data
          const plantData = data || {};

          // Update the plant data with normalized properties
          const updatedPlant = {
            ...plantData,
            totalPower:
              plantData.totalPower ||
              plantData.power ||
              plantData.current_power ||
              0,
            todayEnergy:
              plantData.todayEnergy ||
              plantData.today_energy ||
              plantData.energy_today ||
              0,
            monthEnergy:
              plantData.monthEnergy ||
              plantData.month_energy ||
              plantData.energy_month ||
              0,
            totalEnergy:
              plantData.totalEnergy ||
              plantData.total_energy ||
              plantData.energy_total ||
              0,
            lastUpdateTime:
              plantData.lastUpdateTime ||
              plantData.last_update_time ||
              originalPlant.lastUpdateTime,
            formattedLastUpdate: this.formatLastUpdateTime(
              plantData.lastUpdateTime ||
                plantData.last_update_time ||
                originalPlant.lastUpdateTime
            ),
          };

          // Update the plant in the plants array
          this.plants[plantIndex] = {
            ...updatedPlant,
            isRefreshing: false,
          };

          // Update the filtered plants array
          this.filterPlants();

          // Update the cache
          this.cachePlants(this.plants);

          // Show success message
          this.showToast(
            `${updatedPlant.plantName || "Plant"} data refreshed successfully`
          );
        })
        .catch((error) => {
          clearTimeout(timeoutId);
          console.error(`Error fetching plant ${plantId}:`, error);

          // Restore original plant data
          this.plants[plantIndex] = {
            ...originalPlant,
            isRefreshing: false,
          };

          // Show error message
          this.showToast(`Failed to refresh plant: ${error.message}`, "error");
        })
        .finally(() => {
          // Ensure loading state is cleared
          this.plants[plantIndex].isRefreshing = false;
        });
    },

    // Show plant details modal
    showPlantDetails(plant) {
      this.selectedPlant = plant;
      this.showPlantDetailModal = true;
      this.isLoadingDetails = true;
      this.detailsCurrentPage = 1;

      fetchPlantDetails(plant.id)
        .then((details) => {
          this.selectedPlantDetails = details;
          this.updateDetailsPagination();
          this.isLoadingDetails = false;
        })
        .catch((error) => {
          console.error("Error fetching plant details:", error);
          this.isLoadingDetails = false;
          this.showToast(
            "Failed to load plant details. Please try again.",
            "error"
          );
        });
    },

    /**
     * Open plant detail modal and load plant details
     * @param {Object} plant - The plant to show details for
     */
    openPlantDetails(plant) {
      this.selectedPlant = plant;
      this.showPlantDetailModal = true;
      this.isLoadingDetails = true;
      this.detailsCurrentPage = 1;

      // Convert plant object to entries for pagination
      this.plantDetails = { ...plant };
      this.updateDetailsPagination();
      this.isLoadingDetails = false;
    },

    /**
     * Update plant details pagination
     */
    updateDetailsPagination() {
      const entries = Object.entries(this.plantDetails);
      this.detailsTotalPages = Math.ceil(entries.length / this.detailsPerPage);

      // Get entries for current page
      const startIndex = (this.detailsCurrentPage - 1) * this.detailsPerPage;
      const endIndex = startIndex + parseInt(this.detailsPerPage);
      const currentEntries = entries.slice(startIndex, endIndex);

      // Convert back to object
      this.paginatedPlantDetails = {};
      currentEntries.forEach(([key, value]) => {
        this.paginatedPlantDetails[key] = value;
      });
    },

    // Show a toast message
    showToast(message, type = "success") {
      // Check if we have the toast function available (typically added globally)
      if (typeof window.showToast === "function") {
        window.showToast(message, type);
      } else {
        // Fallback to console if toast function not available
        console.log(`Toast (${type}): ${message}`);
      }
    },

    // Format the last update time in a more user-friendly way
    formatLastUpdateTime(dateTimeString) {
      if (!dateTimeString) return "N/A";

      try {
        const date = new Date(dateTimeString);

        // If invalid date, return original string
        if (isNaN(date.getTime())) return dateTimeString;

        // Check if it's today
        const today = new Date();
        const isToday =
          date.getDate() === today.getDate() &&
          date.getMonth() === today.getMonth() &&
          date.getFullYear() === today.getFullYear();

        if (isToday) {
          // For today, show just the time
          return date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          });
        } else {
          // For other days, show date and time
          return (
            date.toLocaleDateString([], {
              month: "short",
              day: "numeric",
            }) +
            " " +
            date.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })
          );
        }
      } catch (e) {
        console.error("Error formatting date:", e);
        return dateTimeString;
      }
    },

    // Sort plants by field
    sortBy(field) {
      if (this.sortField === field) {
        this.sortAsc = !this.sortAsc;
      } else {
        this.sortField = field;
        this.sortAsc = true;
      }

      this.sortPlants();
    },

    // Apply sorting to filtered plants
    sortPlants() {
      const field = this.sortField;
      const direction = this.sortAsc ? 1 : -1;

      this.filteredPlants.sort((a, b) => {
        let aValue = a[field];
        let bValue = b[field];

        // Handle undefined values
        if (aValue === undefined) aValue = "";
        if (bValue === undefined) bValue = "";

        // Convert to appropriate types for comparison
        if (typeof aValue === "string") {
          return direction * aValue.localeCompare(bValue);
        } else {
          return direction * (aValue - bValue);
        }
      });
    },

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

    // Format power value with unit
    formatPower(power) {
      if (power === undefined || power === null) return "N/A";

      // Format to 2 decimal places
      const formattedPower =
        typeof power === "number" ? power.toFixed(2) : power;
      return `${formattedPower} kW`;
    },

    // Format energy value with unit
    formatEnergy(energy) {
      if (energy === undefined || energy === null) return "N/A";

      // Format to 2 decimal places
      const formattedEnergy =
        typeof energy === "number" ? energy.toFixed(2) : energy;
      return `${formattedEnergy} kWh`;
    },

    // Get status text
    getStatusText(status) {
      const statusMap = {
        active: "Active",
        inactive: "Inactive",
        maintenance: "Maintenance",
        error: "Error",
      };
      return statusMap[status] || "Unknown";
    },

    // Get status CSS class
    getStatusClass(status) {
      const classMap = {
        active: "status-active",
        inactive: "status-inactive",
        maintenance: "status-maintenance",
        error: "status-error",
      };
      return classMap[status] || "status-inactive";
    },

    // Get status badge class for cards
    getStatusBadgeClass(status) {
      const classMap = {
        active: "bg-green-600",
        inactive: "bg-gray-500",
        maintenance: "bg-amber-500",
        error: "bg-red-600",
      };
      return classMap[status] || "bg-gray-500";
    },

    // Handle image error
    handleImageError(event) {
      event.target.src = "/static/images/default-plant.jpg";
    },

    // Format key names for display
    formatKeyName(key) {
      return formatKeyName(key);
    },

    // Format plant values based on key type
    formatPlantValue(key, value) {
      return formatPlantValue(key, value);
    },

    // Export filtered plants to Excel
    exportToExcel() {
      if (this.filteredPlants.length === 0) {
        this.errorMessage = "No data to export.";
        return;
      }

      // Get current date and time for filename and header
      const now = new Date();
      const exportTime = now.toLocaleString();
      const timestamp = now
        .toISOString()
        .replace(/[:.]/g, "-")
        .substring(0, 19);
      const filename = `growatt_plants_${timestamp}.csv`;

      // Show visual feedback when exporting
      const exportBtn = document.getElementById("export-excel-button");
      const originalText = exportBtn.innerHTML;
      exportBtn.innerHTML =
        '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg><span>Exporting...</span>';
      exportBtn.disabled = true;

      try {
        // Create CSV content with BOM for UTF-8 (helps Excel recognize UTF-8)
        let csvContent = "\uFEFF";

        // Add header information with export time
        csvContent += `"Growatt Plants Export - ${exportTime}"\n`;
        csvContent += `"Export Time: ${exportTime}"\n`;
        csvContent += `"Total Plants: ${this.filteredPlants.length}"\n\n`;

        // Add data table headers (using proper column names)
        csvContent +=
          [
            "Plant ID",
            "Plant Name",
            "Status",
            "Timezone",
            "Total Power (kW)",
            "Today Energy (kWh)",
            "Month Energy (kWh)",
            "Total Energy (kWh)",
            "Location",
            "Last Updated",
            "Country",
          ]
            .map((header) => `"${header}"`)
            .join(",") + "\n";

        // Add data rows with all available information
        this.filteredPlants.forEach((plant) => {
          const row = [
            plant.id || "",
            plant.plantName || "",
            this.getStatusText(plant.status || "active"),
            this.formatTimezone(plant.timezone),
            plant.totalPower || "0",
            plant.todayEnergy || "0",
            plant.monthEnergy || "0",
            plant.totalEnergy || "0",
            plant.location || "",
            plant.lastUpdateTime || "",
            plant.country || "",
          ]
            .map((cell) => `"${cell.toString().replace(/"/g, '""')}"`)
            .join(",");

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

        // Show success notification
        this.showToast("Export completed successfully");
      } catch (error) {
        console.error("Error exporting to Excel:", error);
        this.errorMessage = `Failed to export: ${error.message}`;
        this.showToast("Export failed: " + error.message, "error");
      } finally {
        // Restore button state
        exportBtn.innerHTML = originalText;
        exportBtn.disabled = false;
      }
    },
  }));
});
