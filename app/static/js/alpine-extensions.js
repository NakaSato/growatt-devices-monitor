/**
 * Alpine.js Extensions
 * Custom extensions to enhance Alpine.js functionality
 */
document.addEventListener("alpine:init", () => {
  // Global component registry
  Alpine.store("components", {
    registry: {},

    register(name, component) {
      this.registry[name] = component;
    },

    get(name) {
      return this.registry[name];
    },
  });

  // Pagination utility
  Alpine.data("pagination", (config = {}) => {
    return {
      currentPage: 1,
      pageSize: config.pageSize || 10,
      totalItems: config.totalItems || 0,

      init() {
        this.$watch("totalItems", () => {
          if (this.currentPage > this.totalPages && this.totalPages > 0) {
            this.currentPage = 1;
          }
        });
      },

      get totalPages() {
        return Math.ceil(this.totalItems / this.pageSize);
      },

      goToPage(page) {
        if (page >= 1 && page <= this.totalPages) {
          this.currentPage = page;
          window.scrollTo({ top: 0, behavior: "smooth" });
          this.$dispatch("pagination-changed", { page });
        }
      },

      nextPage() {
        this.goToPage(this.currentPage + 1);
      },

      prevPage() {
        this.goToPage(this.currentPage - 1);
      },

      getPageItems(items) {
        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        return items.slice(start, end);
      },
    };
  });

  // Data fetching utility
  Alpine.data("dataFetcher", (config = {}) => {
    return {
      data: [],
      isLoading: true,
      hasError: false,
      errorMessage: "",
      lastFetched: null,
      cacheDuration: config.cacheDuration || 5 * 60 * 1000, // 5 minutes by default

      init() {
        this.fetchData(config.url);
      },

      async fetchData(url, forceFresh = false) {
        if (!url) return;

        this.isLoading = true;
        this.hasError = false;

        try {
          // Check for cached data
          const cacheKey = `data-cache-${url}`;
          const cachedData = !forceFresh && localStorage.getItem(cacheKey);

          if (cachedData) {
            try {
              const parsed = JSON.parse(cachedData);
              if (Date.now() - parsed.timestamp < this.cacheDuration) {
                this.data = parsed.data;
                this.lastFetched = new Date(parsed.timestamp);
                this.isLoading = false;
                return;
              }
            } catch (e) {
              console.warn("Failed to parse cached data", e);
              // Continue with fetch
            }
          }

          // Fetch fresh data
          const response = await fetch(url);

          if (!response.ok) {
            throw new Error(
              `API Error: ${response.status} ${response.statusText}`
            );
          }

          const jsonData = await response.json();
          this.data = jsonData;
          this.lastFetched = new Date();

          // Cache the data
          localStorage.setItem(
            cacheKey,
            JSON.stringify({
              data: jsonData,
              timestamp: Date.now(),
            })
          );
        } catch (error) {
          this.hasError = true;
          this.errorMessage = error.message || "Failed to fetch data";
          console.error("Data fetching error:", error);
        } finally {
          this.isLoading = false;
        }
      },

      refresh() {
        return this.fetchData(config.url, true);
      },
    };
  });

  // Format utilities
  Alpine.data("formatter", () => {
    return {
      formatNumber(value, options = {}) {
        if (value === null || value === undefined) return "-";
        return new Intl.NumberFormat(options.locale || "en-US", {
          maximumFractionDigits: options.decimals || 2,
          minimumFractionDigits: options.minDecimals || 0,
          ...options,
        }).format(value);
      },

      formatCurrency(value, options = {}) {
        return this.formatNumber(value, {
          style: "currency",
          currency: options.currency || "USD",
          ...options,
        });
      },

      formatPercent(value, options = {}) {
        return this.formatNumber(value, {
          style: "percent",
          maximumFractionDigits: options.decimals || 1,
          ...options,
        });
      },

      formatDate(value, options = {}) {
        if (!value) return "-";
        try {
          const date = new Date(value);
          return new Intl.DateTimeFormat(options.locale || "en-US", {
            year: options.year || "numeric",
            month: options.month || "short",
            day: options.day || "numeric",
            hour: options.hour,
            minute: options.minute,
            second: options.second,
            ...options,
          }).format(date);
        } catch (e) {
          console.warn("Date formatting error:", e);
          return value;
        }
      },

      formatPower(value) {
        if (value === null || value === undefined) return "-";

        if (value >= 1000) {
          return `${this.formatNumber(value / 1000, { decimals: 2 })} MW`;
        }

        return `${this.formatNumber(value, { decimals: 2 })} kW`;
      },

      formatEnergy(value) {
        if (value === null || value === undefined) return "-";

        if (value >= 1000) {
          return `${this.formatNumber(value / 1000, { decimals: 2 })} MWh`;
        }

        return `${this.formatNumber(value, { decimals: 2 })} kWh`;
      },

      formatDuration(seconds) {
        if (!seconds && seconds !== 0) return "-";

        const days = Math.floor(seconds / (24 * 3600));
        const hours = Math.floor((seconds % (24 * 3600)) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        if (days > 0) {
          return `${days}d ${hours}h ${minutes}m`;
        }

        if (hours > 0) {
          return `${hours}h ${minutes}m`;
        }

        return `${minutes}m`;
      },

      formatRelativeTime(date) {
        if (!date) return "-";

        try {
          const now = new Date();
          const targetDate = new Date(date);
          const diffInSeconds = Math.floor((now - targetDate) / 1000);

          if (diffInSeconds < 60) {
            return "Just now";
          }

          if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
          }

          if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours} hour${hours > 1 ? "s" : ""} ago`;
          }

          const days = Math.floor(diffInSeconds / 86400);
          return `${days} day${days > 1 ? "s" : ""} ago`;
        } catch (e) {
          console.warn("Relative time formatting error:", e);
          return date;
        }
      },
    };
  });
});
