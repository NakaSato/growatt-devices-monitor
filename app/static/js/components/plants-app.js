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
    viewMode: window.innerWidth < 640 ? "cards" : "table", // Default to cards on smaller screens, table on larger ones
    searchQuery: "",
    statusFilter: "all",
    sortField: "plantName", // Default sort field
    sortAsc: true, // Default sort direction

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

      this.fetchPlants();
    },

    fetchPlants() {
      this.isLoading = true;
      this.errorMessage = "";

      fetch("/api/management/data")
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          // Extract plants from management data structure
          const plantData = data.plants || [];
          
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
            };
          });
          
          this.filteredPlants = [...this.plants]; // Initialize filtered plants
          this.sortPlants(); // Apply initial sort
          console.log("Plants data:", this.plants);
        })
        .catch((error) => {
          console.error("Error fetching plants:", error);
          this.errorMessage = `Failed to load plants: ${error.message}`;
        })
        .finally(() => {
          this.isLoading = false;
        });
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
          (plant.id && plant.id.toString().includes(this.searchQuery));

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
      return `${power} kW`;
    },

    // Format energy value with unit
    formatEnergy(energy) {
      if (energy === undefined || energy === null) return "N/A";
      return `${energy} kWh`;
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
      event.target.src =
        "{{ url_for('static', filename='images/default-plant.jpg') }}";
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
      } catch (error) {
        console.error("Error exporting to Excel:", error);
        this.errorMessage = `Failed to export: ${error.message}`;
      } finally {
        // Restore button state
        exportBtn.innerHTML = originalText;
        exportBtn.disabled = false;
      }
    },
  }));
});
