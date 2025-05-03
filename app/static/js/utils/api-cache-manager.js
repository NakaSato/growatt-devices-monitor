/**
 * Enhanced API Cache Manager
 *
 * Provides consistent caching behavior between client and server,
 * with support for cache invalidation and cache control headers.
 */
window.ApiCacheManager = (function () {
  // Default settings
  const DEFAULT_SETTINGS = {
    enabled: true,
    defaultCacheDuration: 5 * 60 * 1000, // 5 minutes in milliseconds
    bypassBrowserCache: true, // Add timestamp to URLs to bypass browser cache
    statusEndpoint: "/api/cache-stats", // Endpoint for checking cache status
    clearCacheEndpoint: "/api/clear-cache", // Endpoint for clearing cache
  };

  // Current settings (will be initialized with defaults + user preferences)
  let settings = { ...DEFAULT_SETTINGS };

  // Cache statistics
  let cacheStats = null;

  return {
    /**
     * Initialize the cache manager with custom settings
     * @param {Object} customSettings - Override default settings
     */
    init: function (customSettings = {}) {
      // Merge default settings with custom settings
      settings = { ...DEFAULT_SETTINGS, ...customSettings };

      console.log("API Cache Manager initialized with settings:", settings);

      // Try to load user preferences from localStorage
      this.loadPreferences();

      return this;
    },

    /**
     * Load cache preferences from localStorage
     */
    loadPreferences: function () {
      try {
        const storedPrefs = localStorage.getItem("apiCachePreferences");
        if (storedPrefs) {
          const prefs = JSON.parse(storedPrefs);
          // Only override specific settings that can be user-controlled
          if (prefs.hasOwnProperty("enabled")) settings.enabled = prefs.enabled;
          if (prefs.hasOwnProperty("defaultCacheDuration")) {
            settings.defaultCacheDuration = prefs.defaultCacheDuration;
          }
          console.log("Loaded cache preferences:", prefs);
        }
      } catch (e) {
        console.warn("Failed to load cache preferences:", e);
      }
    },

    /**
     * Save cache preferences to localStorage
     */
    savePreferences: function () {
      try {
        const prefsToSave = {
          enabled: settings.enabled,
          defaultCacheDuration: settings.defaultCacheDuration,
        };
        localStorage.setItem(
          "apiCachePreferences",
          JSON.stringify(prefsToSave)
        );
        console.log("Saved cache preferences:", prefsToSave);
      } catch (e) {
        console.warn("Failed to save cache preferences:", e);
      }
    },

    /**
     * Enable or disable caching
     * @param {boolean} enabled - Whether caching should be enabled
     */
    setEnabled: function (enabled) {
      settings.enabled = !!enabled;
      this.savePreferences();
      return this;
    },

    /**
     * Set the default cache duration
     * @param {number} durationMs - Duration in milliseconds
     */
    setDefaultCacheDuration: function (durationMs) {
      settings.defaultCacheDuration = durationMs;
      this.savePreferences();
      return this;
    },

    /**
     * Generate a cache key for a URL
     * @param {string} url - The URL to generate a key for
     * @returns {string} The cache key
     */
    getCacheKey: function (url) {
      // Remove any query parameters after a ? in the URL for the cache key
      const baseUrl = url.split("?")[0];
      return `api_cache_${baseUrl}`;
    },

    /**
     * Get cached data for a URL if it exists and is valid
     * @param {string} url - The URL to check cache for
     * @param {number} maxAge - Maximum age of the cache in milliseconds
     * @returns {Object|null} The cached data or null if not found or expired
     */
    get: function (url, maxAge = null) {
      if (!settings.enabled) return null;

      const cacheKey = this.getCacheKey(url);
      const cachedData = localStorage.getItem(cacheKey);

      if (!cachedData) return null;

      try {
        const parsed = JSON.parse(cachedData);
        const cacheAge = Date.now() - parsed.timestamp;
        const maxCacheAge = maxAge || settings.defaultCacheDuration;

        // Check if cache is still valid
        if (cacheAge < maxCacheAge) {
          console.log(
            `Using cached data for ${url} (age: ${Math.round(
              cacheAge / 1000
            )}s)`
          );
          return parsed.data;
        } else {
          console.log(
            `Cache expired for ${url} (age: ${Math.round(cacheAge / 1000)}s)`
          );
          return null;
        }
      } catch (err) {
        console.warn("Invalid cache data for", url, err);
        return null;
      }
    },

    /**
     * Store response data in cache
     * @param {string} url - The URL to cache data for
     * @param {Object} data - The data to cache
     */
    set: function (url, data) {
      if (!settings.enabled) return;

      const cacheKey = this.getCacheKey(url);
      try {
        localStorage.setItem(
          cacheKey,
          JSON.stringify({
            timestamp: Date.now(),
            data: data,
          })
        );
        console.log(`Cached data for ${url}`);
      } catch (err) {
        console.warn("Failed to cache data:", err);
      }
    },

    /**
     * Clear specific or all cached responses
     * @param {string} url - Optional specific URL to clear from cache
     */
    clear: function (url) {
      if (url) {
        const cacheKey = this.getCacheKey(url);
        localStorage.removeItem(cacheKey);
        console.log(`Cleared cache for ${url}`);
      } else {
        // Clear all API cache entries
        Object.keys(localStorage).forEach((key) => {
          if (key.startsWith("api_cache_")) {
            localStorage.removeItem(key);
          }
        });
        console.log("Cleared all API cache");
      }

      // Also clear server-side cache if clear endpoint is provided
      if (settings.clearCacheEndpoint) {
        fetch(settings.clearCacheEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ source: "client" }),
        })
          .then((response) => response.json())
          .then((data) => {
            console.log("Server cache cleared:", data);
          })
          .catch((error) => {
            console.error("Failed to clear server cache:", error);
          });
      }
    },

    /**
     * Fetch data from a URL with caching
     * @param {string} url - The URL to fetch data from
     * @param {Object} options - Options for the fetch
     * @returns {Promise<Object>} The fetched data
     */
    fetch: async function (url, options = {}) {
      const {
        forceFresh = false,
        cacheDuration = null,
        requestOptions = {},
        bypassBrowserCache = settings.bypassBrowserCache,
      } = options;

      // Try to get from cache unless force refresh is requested
      if (!forceFresh && settings.enabled) {
        const cachedData = this.get(url, cacheDuration);
        if (cachedData) return cachedData;
      }

      // Add timestamp to URL to bypass browser cache if needed
      const urlWithTimestamp = bypassBrowserCache
        ? `${url}${url.includes("?") ? "&" : "?"}_t=${Date.now()}`
        : url;

      // Add cache control header if force refresh
      const headers = {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(forceFresh ? { "Cache-Control": "no-cache" } : {}),
        ...requestOptions.headers,
      };

      try {
        // Fetch fresh data
        const response = await fetch(urlWithTimestamp, {
          headers,
          ...requestOptions,
        });

        if (!response.ok) {
          throw new Error(
            `API Error: ${response.status} ${response.statusText}`
          );
        }

        const responseData = await response.json();

        // Cache the response if caching is enabled and not forcing fresh
        if (settings.enabled && !forceFresh) {
          this.set(url, responseData);
        }

        return responseData;
      } catch (error) {
        console.error(`Error fetching ${url}:`, error);
        throw error;
      }
    },

    /**
     * Get cache statistics from the server
     * @returns {Promise<Object>} Cache statistics
     */
    getStats: async function () {
      try {
        if (!settings.statusEndpoint) {
          return { clientCache: this.getClientStats() };
        }

        const response = await fetch(settings.statusEndpoint);
        if (!response.ok) {
          throw new Error(`Failed to get cache stats: ${response.status}`);
        }

        const data = await response.json();
        cacheStats = data;

        // Add client-side stats
        data.clientCache = this.getClientStats();

        return data;
      } catch (error) {
        console.error("Error fetching cache stats:", error);
        return { error: error.message, clientCache: this.getClientStats() };
      }
    },

    /**
     * Get client-side cache statistics
     * @returns {Object} Client cache statistics
     */
    getClientStats: function () {
      let totalSize = 0;
      let count = 0;
      const urlStats = {};

      // Calculate cache size and stats
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith("api_cache_")) {
          const item = localStorage.getItem(key);
          totalSize += item.length;
          count++;

          try {
            const data = JSON.parse(item);
            const url = key.replace("api_cache_", "");
            const age = Math.round((Date.now() - data.timestamp) / 1000);

            urlStats[url] = {
              size: item.length,
              age_seconds: age,
            };
          } catch (e) {
            // Skip invalid entries
          }
        }
      });

      return {
        entries: count,
        size_bytes: totalSize,
        size_formatted: this.formatSize(totalSize),
        url_stats: urlStats,
        enabled: settings.enabled,
        defaultCacheDuration: settings.defaultCacheDuration,
      };
    },

    /**
     * Format a size in bytes to a human-readable string
     * @param {number} bytes - The size in bytes
     * @returns {string} Formatted size string
     */
    formatSize: function (bytes) {
      if (bytes < 1024) return bytes + " bytes";
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
      return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    },
  };
})();
