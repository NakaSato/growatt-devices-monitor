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

    // Pagination
    currentPage: 1,
    pageSize: window.innerWidth < 640 ? 6 : 10, // Smaller page size on mobile

    // Computed property for page numbers
    get pageNumbers() {
      const totalPages = this.totalPages;
      const currentPage = this.currentPage;

      if (totalPages <= 5) {
        return Array.from({ length: totalPages }, (_, i) => i + 1);
      }

      if (currentPage <= 3) {
        return [1, 2, 3, 4, 5];
      }

      if (currentPage >= totalPages - 2) {
        return Array.from({ length: 5 }, (_, i) => totalPages - 4 + i);
      }

      return [
        currentPage - 2,
        currentPage - 1,
        currentPage,
        currentPage + 1,
        currentPage + 2,
      ];
    },

    // Computed property for total pages
    get totalPages() {
      return Math.ceil(this.filteredPlants.length / this.pageSize);
    },

    // Computed property for paginated plants
    get paginatedPlants() {
      const start = (this.currentPage - 1) * this.pageSize;
      const end = start + this.pageSize;
      return this.filteredPlants.slice(start, end);
    },

    // Lifecycle hooks - Initialize with responsive settings
    init() {
      // Responsive view mode toggle based on screen size
      window.addEventListener("resize", () => {
        // Only auto-switch view mode if the user hasn't manually selected one
        if (!localStorage.getItem("preferredViewMode")) {
          this.viewMode = window.innerWidth < 640 ? "cards" : "table";
        }

        // Update page size when screen size changes
        this.pageSize = window.innerWidth < 640 ? 6 : 10;

        // Reset to page 1 if the current page would be out of bounds after resize
        if (this.currentPage > this.totalPages && this.totalPages > 0) {
          this.currentPage = 1;
        }
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

    // Set up a periodic refresh if the tab is visible (every 5 minutes)
    setupPeriodicRefresh() {
      const refreshInterval = 5 * 60 * 1000; // 5 minutes in milliseconds

      // Use setInterval for periodic refresh
      setInterval(() => {
        // Only refresh if the document is visible and we're not already loading
        if (
          document.visibilityState === "visible" &&
          !this.isLoading &&
          !this.isRefreshing
        ) {
          this.fetchPlants(true); // Silent refresh
        }
      }, refreshInterval);

      // Also refresh when the tab becomes visible again
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && this.lastFetchTime) {
          const timeSinceLastFetch = Date.now() - this.lastFetchTime;
          if (
            timeSinceLastFetch > refreshInterval &&
            !this.isLoading &&
            !this.isRefreshing
          ) {
            this.fetchPlants(true); // Silent refresh when tab becomes visible
          }
        }
      });
    },

    // Get cached plants data
    getCachedPlants() {
      const cachedData = localStorage.getItem("plantsCache");
      if (!cachedData) return null;

      try {
        const { timestamp, plants } = JSON.parse(cachedData);
        const now = Date.now();

        // Check if cache is still valid
        if (
          now - timestamp < this.cacheDuration &&
          plants &&
          plants.length > 0
        ) {
          this.lastFetchTime = timestamp;
          return plants;
        }
      } catch (e) {
        console.error("Error parsing cached plants data:", e);
      }

      return null;
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

    fetchPlants(silentRefresh = false) {
      // If this is a silent refresh, don't show loading indicator
      if (!silentRefresh) {
        this.isLoading = true;
      } else {
        this.isRefreshing = true;
      }

      this.errorMessage = "";
      this.fetchRetryCount = 0;

      this.performFetch();
    },

    performFetch() {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

      fetch("/api/plants", {
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
          // Extract plants from data structure
          const plantData = Array.isArray(data) ? data : data.plants || [];

          // Process the data
          this.plants = plantData.map((plant) => {
            // Normalize property names to ensure consistency
            return {
              ...plant,
              // Ensure these properties exist with expected names
              totalPower:
                plant.totalPower || plant.power || plant.current_power || 0,
              todayEnergy:
                plant.todayEnergy ||
                plant.today_energy ||
                plant.energy_today ||
                0,
              monthEnergy:
                plant.monthEnergy ||
                plant.month_energy ||
                plant.energy_month ||
                0,
              totalEnergy:
                plant.totalEnergy ||
                plant.total_energy ||
                plant.energy_total ||
                0,
              lastUpdateTime:
                plant.lastUpdateTime || plant.last_update_time || "",
              // Add a formatted last update time for easier display
              formattedLastUpdate: this.formatLastUpdateTime(
                plant.lastUpdateTime || plant.last_update_time || ""
              ),
            };
          });

          // Cache the plant data for future use
          this.cachePlants(this.plants);

          this.filteredPlants = [...this.plants]; // Initialize filtered plants
          this.sortPlants(); // Apply initial sort
          console.log("Plants data refreshed:", this.plants);

          // Check if we need to show a success message for manual refresh
          if (!this.isRefreshing && !this.isLoading) {
            // Show success toast or notification if needed for manual refresh
            this.showToast("Plants data refreshed successfully");
          }
        })
        .catch((error) => {
          clearTimeout(timeoutId);
          console.error("Error fetching plants:", error);

          // For network timeout or abort errors, retry
          if (
            error.name === "AbortError" ||
            error.name === "TimeoutError" ||
            error.message.includes("timeout") ||
            error.message.includes("network")
          ) {
            if (this.fetchRetryCount < this.maxRetries) {
              this.fetchRetryCount++;
              const delay =
                this.retryDelay * Math.pow(2, this.fetchRetryCount - 1); // Exponential backoff
              console.log(
                `Retrying fetch (${this.fetchRetryCount}/${this.maxRetries}) in ${delay}ms...`
              );
              setTimeout(() => this.performFetch(), delay);
              return;
            }
          }

          // Only show error for non-silent refreshes or after all retries failed
          if (!this.isRefreshing || this.fetchRetryCount >= this.maxRetries) {
            this.errorMessage = `Failed to load plants: ${error.message}`;
          }

          // If we have cached data, use it as fallback
          const cachedPlants = this.getCachedPlants();
          if (cachedPlants && this.plants.length === 0) {
            this.plants = cachedPlants;
            this.filteredPlants = [...this.plants];
            this.sortPlants();

            // Show notification that we're using cached data
            console.log("Using cached plants data due to fetch error");
            if (!this.isRefreshing) {
              this.showToast(
                "Using cached data - please check your connection",
                "warning"
              );
            }
          }
        })
        .finally(() => {
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

    // Filter plants based on search and status filter
    filterPlants() {
      this.currentPage = 1; // Reset to first page when filtering

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

    // Pagination methods
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
      this.currentPage = page;
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
