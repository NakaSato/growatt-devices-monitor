/**
 * responsive-utils.js - Utilities for responsive design
 * This file provides functionality for detecting screen sizes and
 * managing responsive behavior across the application.
 */

class ResponsiveManager {
  constructor(options = {}) {
    this.breakpoints = {
      xs: options.xs || 480,
      sm: options.sm || 640,
      md: options.md || 768,
      lg: options.lg || 1024,
      xl: options.xl || 1280,
      "2xl": options["2xl"] || 1536,
    };

    this.currentBreakpoint = this.getCurrentBreakpoint();
    this.initializeEventListeners();
  }

  /**
   * Initialize event listeners for responsive behavior
   */
  initializeEventListeners() {
    // Debounced resize handler
    let resizeTimeout;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => this.handleResize(), 100);
    });

    // Initialize responsive state
    this.updateResponsiveState();
  }

  /**
   * Handle window resize events
   */
  handleResize() {
    const newBreakpoint = this.getCurrentBreakpoint();
    const breakpointChanged = newBreakpoint !== this.currentBreakpoint;

    // Update responsive state
    this.updateResponsiveState();

    // If breakpoint changed, dispatch event
    if (breakpointChanged) {
      this.currentBreakpoint = newBreakpoint;
      this.dispatchBreakpointEvent(newBreakpoint);
    }
  }

  /**
   * Update the global responsive state object
   */
  updateResponsiveState() {
    const width = window.innerWidth;
    const height = window.innerHeight;

    // Create or update window.responsive object
    window.responsive = {
      width,
      height,
      breakpoint: this.currentBreakpoint,
      isMobile: width < this.breakpoints.sm,
      isTablet: width >= this.breakpoints.sm && width < this.breakpoints.lg,
      isDesktop: width >= this.breakpoints.lg,
      isPortrait: height > width,
      isLandscape: width >= height,
      touch: "ontouchstart" in window || navigator.maxTouchPoints > 0,
    };

    // Apply responsive data attributes to document element for CSS use
    document.documentElement.setAttribute(
      "data-breakpoint",
      this.currentBreakpoint
    );
    document.documentElement.setAttribute(
      "data-device",
      window.responsive.isMobile
        ? "mobile"
        : window.responsive.isTablet
        ? "tablet"
        : "desktop"
    );

    // Dispatch the responsive-changed event
    this.dispatchResponsiveEvent();
  }

  /**
   * Get the current breakpoint based on window width
   */
  getCurrentBreakpoint() {
    const width = window.innerWidth;

    if (width < this.breakpoints.xs) return "xxs";
    if (width < this.breakpoints.sm) return "xs";
    if (width < this.breakpoints.md) return "sm";
    if (width < this.breakpoints.lg) return "md";
    if (width < this.breakpoints.xl) return "lg";
    if (width < this.breakpoints["2xl"]) return "xl";
    return "2xl";
  }

  /**
   * Dispatch a custom event when responsive state changes
   */
  dispatchResponsiveEvent() {
    const event = new CustomEvent("responsive-changed", {
      detail: window.responsive,
      bubbles: true,
    });
    window.dispatchEvent(event);
  }

  /**
   * Dispatch a custom event when breakpoint changes
   */
  dispatchBreakpointEvent(breakpoint) {
    const event = new CustomEvent("breakpoint-changed", {
      detail: {
        breakpoint,
        previous: this.currentBreakpoint,
      },
      bubbles: true,
    });
    window.dispatchEvent(event);
  }
}

// Initialize responsive manager when the DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
  // Create the responsive manager instance
  window.responsiveManager = new ResponsiveManager();

  // Add helper classes to the document for CSS usage
  document.body.classList.add("js-responsive-ready");
});
