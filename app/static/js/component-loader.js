/**
 * Component Loader
 * Utility for loading components dynamically
 */
class ComponentLoader {
  constructor(options = {}) {
    this.options = {
      templatePath: "/templates/components/",
      cacheDuration: 3600, // 1 hour in seconds
      preload: [],
      onError: (error) => console.error(error),
      ...options,
    };

    this.componentCache = {};
    this.loadingPromises = {};

    // Preload components if specified
    if (
      Array.isArray(this.options.preload) &&
      this.options.preload.length > 0
    ) {
      this.options.preload.forEach((componentName) => {
        this.preloadComponent(componentName);
      });
    }
  }

  /**
   * Preload a component
   * @param {string} componentName - The name of the component to preload
   */
  preloadComponent(componentName) {
    this.getComponent(componentName).catch((error) =>
      this.options.onError(
        `Failed to preload component "${componentName}": ${error}`
      )
    );
  }

  /**
   * Get a component by name
   * @param {string} componentName - The name of the component
   * @returns {Promise<string>} - The component HTML
   */
  getComponent(componentName) {
    // Check cache first
    const cached = this.getCachedComponent(componentName);
    if (cached) {
      return Promise.resolve(cached);
    }

    // Prevent duplicate loading of the same component
    if (this.loadingPromises[componentName]) {
      return this.loadingPromises[componentName];
    }

    // Load the component
    const loadPromise = this.fetchComponent(componentName)
      .then((html) => {
        this.cacheComponent(componentName, html);
        delete this.loadingPromises[componentName];
        return html;
      })
      .catch((error) => {
        delete this.loadingPromises[componentName];
        this.options.onError(
          `Failed to load component "${componentName}": ${error}`
        );
        throw error;
      });

    this.loadingPromises[componentName] = loadPromise;
    return loadPromise;
  }

  /**
   * Get a component from cache
   * @param {string} componentName - The name of the component
   * @returns {string|null} - The cached component HTML or null if not cached
   */
  getCachedComponent(componentName) {
    const cached = this.componentCache[componentName];
    if (!cached) return null;

    // Check if cache is expired
    if (Date.now() > cached.expires) {
      delete this.componentCache[componentName];
      return null;
    }

    return cached.html;
  }

  /**
   * Cache a component
   * @param {string} componentName - The name of the component
   * @param {string} html - The component HTML
   */
  cacheComponent(componentName, html) {
    this.componentCache[componentName] = {
      html,
      expires: Date.now() + this.options.cacheDuration * 1000,
    };
  }

  /**
   * Fetch a component from the server
   * @param {string} componentName - The name of the component
   * @returns {Promise<string>} - The component HTML
   */
  fetchComponent(componentName) {
    const url = `${this.options.templatePath}${componentName}.html`;

    return fetch(url).then((response) => {
      if (!response.ok) {
        throw new Error(
          `Component "${componentName}" not found (${response.status})`
        );
      }
      return response.text();
    });
  }

  /**
   * Render a component into an element
   * @param {string} componentName - The name of the component
   * @param {HTMLElement} targetElement - The element to render into
   * @param {Object} props - Props to pass to the component
   * @returns {Promise<void>}
   */
  renderComponent(componentName, targetElement, props = {}) {
    if (!targetElement) {
      this.options.onError(
        `Target element for component "${componentName}" not found`
      );
      return Promise.reject(new Error("Target element not found"));
    }

    return this.getComponent(componentName).then((html) => {
      // Replace props placeholders if any
      Object.entries(props).forEach(([key, value]) => {
        html = html.replace(
          new RegExp(`\\{\\{\\s*${key}\\s*\\}\\}`, "g"),
          value
        );
      });

      targetElement.innerHTML = html;

      // Initialize Alpine components if Alpine is available
      if (window.Alpine) {
        window.Alpine.initTree(targetElement);
      }

      return targetElement;
    });
  }

  /**
   * Clear the component cache
   * @param {string} [componentName] - Optional component name to clear specific cache
   */
  clearCache(componentName) {
    if (componentName) {
      delete this.componentCache[componentName];
    } else {
      this.componentCache = {};
    }
  }
}

// Export to window
window.ComponentLoader = ComponentLoader;
