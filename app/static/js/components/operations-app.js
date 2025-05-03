/**
 * Operations Application Component
 * Manages system operations and configuration
 */

class OperationsApp {
  constructor() {
    this.config = null;
    this.configForm = document.getElementById("config-form");
    this.statusMessage = document.getElementById("status-message");
    this.saveButton = document.getElementById("save-config");

    this.init();
  }

  /**
   * Initialize the operations application
   */
  async init() {
    try {
      await this.loadConfiguration();
      this.setupEventListeners();
      this.renderConfigForm();
    } catch (error) {
      console.error("Failed to initialize operations app:", error);
      this.showMessage(
        "Error initializing configuration. Check console for details.",
        "error"
      );
    }
  }

  /**
   * Load configuration data from the API
   */
  async loadConfiguration() {
    this.showMessage("Loading configuration...", "info");

    const response = await OperationsUtils.fetchOperationsData();

    if (response.status === "success" && response.config) {
      this.config = response.config;
      this.showMessage("Configuration loaded successfully", "success", 3000);
    } else {
      this.config = OperationsUtils.getDefaultConfig();
      this.showMessage(
        response.message || "Failed to load configuration. Using defaults.",
        "warning"
      );
    }

    console.log("Loaded configuration:", this.config);
  }

  /**
   * Set up event listeners for user interactions
   */
  setupEventListeners() {
    // Save button click event
    if (this.saveButton) {
      this.saveButton.addEventListener("click", async (e) => {
        e.preventDefault();
        await this.saveConfiguration();
      });
    }

    // Form input changes
    if (this.configForm) {
      this.configForm.addEventListener("change", (e) => {
        // Update the config object when inputs change
        const input = e.target;
        if (input.id && input.id.includes(".")) {
          const [section, key] = input.id.split(".");
          let value = input.value;

          // Convert to appropriate type
          if (input.type === "checkbox") {
            value = input.checked;
          } else if (input.type === "number") {
            value = parseFloat(value);
          }

          // Update the configuration
          if (this.config[section]) {
            this.config[section][key] = value;
          }
        }
      });
    }
  }

  /**
   * Render the configuration form
   */
  renderConfigForm() {
    if (!this.configForm || !this.config) return;

    // Render all form fields based on the configuration
    Object.entries(this.config).forEach(([section, options]) => {
      Object.entries(options).forEach(([key, value]) => {
        const inputId = `${section}.${key}`;
        const input = document.getElementById(inputId);

        if (input) {
          if (input.type === "checkbox") {
            input.checked = value;
          } else {
            input.value = value;
          }
        }
      });
    });
  }

  /**
   * Save the configuration to the server
   */
  async saveConfiguration() {
    if (!this.config) return;

    this.showMessage("Saving configuration...", "info");

    try {
      const response = await OperationsUtils.saveConfigData(this.config);

      if (response.status === "success") {
        this.showMessage("Configuration saved successfully", "success");
      } else {
        this.showMessage(
          response.message || "Failed to save configuration",
          "error"
        );
      }
    } catch (error) {
      console.error("Error saving configuration:", error);
      this.showMessage("Error saving configuration", "error");
    }
  }

  /**
   * Display a status message to the user
   * @param {string} message - The message to display
   * @param {string} type - The type of message (success, error, info, warning)
   * @param {number} timeout - Optional timeout to hide the message
   */
  showMessage(message, type = "info", timeout = 0) {
    if (!this.statusMessage) return;

    // Clear any existing classes
    this.statusMessage.className = "status-message";

    // Add the appropriate class
    this.statusMessage.classList.add(`status-${type}`);

    // Set the message
    this.statusMessage.textContent = message;

    // Show the message
    this.statusMessage.style.display = "block";

    // Automatically hide after timeout if specified
    if (timeout > 0) {
      setTimeout(() => {
        this.statusMessage.style.display = "none";
      }, timeout);
    }
  }
}

// Initialize the operations app when the DOM content is loaded
document.addEventListener("DOMContentLoaded", () => {
  window.operationsApp = new OperationsApp();
});
