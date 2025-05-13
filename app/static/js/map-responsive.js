/**
 * Map Responsive Behavior - For better mobile experience
 * Handles responsive behavior for the Solar Plants Map page
 */

document.addEventListener("DOMContentLoaded", function () {
  // Elements to work with
  const mapContainer = document.querySelector(".lg\\:col-span-3");
  const sidebar = document.querySelector(".lg\\:col-span-1");
  const controlsBar = document.querySelector(
    ".bg-white.rounded-xl.shadow-md.mb-6"
  );

  // Mobile toggle button for sidebar
  let mobileToggleBtn;

  // Create and initialize responsive elements
  initResponsiveElements();

  // Handle initial state and add resize listener
  handleResponsiveLayout();
  window.addEventListener("resize", handleResponsiveLayout);

  /**
   * Initialize responsive elements
   */
  function initResponsiveElements() {
    // Create mobile toggle button if it doesn't exist
    if (!document.getElementById("mobile-sidebar-toggle")) {
      mobileToggleBtn = document.createElement("button");
      mobileToggleBtn.id = "mobile-sidebar-toggle";
      mobileToggleBtn.className =
        "fixed bottom-4 left-4 z-50 w-12 h-12 bg-blue-600 text-white rounded-full shadow-lg flex items-center justify-center md:hidden";
      mobileToggleBtn.innerHTML = '<i class="fas fa-info"></i>';
      mobileToggleBtn.setAttribute("aria-label", "Toggle details sidebar");
      document.body.appendChild(mobileToggleBtn);

      // Add click event to toggle sidebar
      mobileToggleBtn.addEventListener("click", toggleMobileSidebar);
    } else {
      mobileToggleBtn = document.getElementById("mobile-sidebar-toggle");
    }

    // Add necessary classes to sidebar for mobile
    if (sidebar && !sidebar.classList.contains("mobile-ready")) {
      sidebar.classList.add("mobile-ready");
      sidebar.dataset.originalClasses = sidebar.className;
    }
  }

  /**
   * Handle responsive layout adjustments
   */
  function handleResponsiveLayout() {
    const isMobile = window.innerWidth < 1024; // lg breakpoint in Tailwind

    if (isMobile) {
      enableMobileLayout();
    } else {
      disableMobileLayout();
    }
  }

  /**
   * Enable mobile-specific layout
   */
  function enableMobileLayout() {
    // Show mobile toggle button
    if (mobileToggleBtn) {
      mobileToggleBtn.classList.remove("hidden");
    }

    // Make map container full width
    if (mapContainer) {
      mapContainer.classList.add("col-span-1", "w-full");
    }

    // Hide sidebar by default on mobile
    if (sidebar) {
      sidebar.classList.add("hidden", "md:block");
      sidebar.classList.add(
        "fixed",
        "inset-0",
        "z-40",
        "bg-white",
        "dark:bg-gray-800",
        "overflow-y-auto"
      );

      // Add close button to sidebar if it doesn't exist
      if (!sidebar.querySelector(".mobile-close-btn")) {
        const closeBtn = document.createElement("button");
        closeBtn.className =
          "mobile-close-btn absolute top-4 right-4 z-50 w-8 h-8 flex items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700 lg:hidden";
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.addEventListener("click", toggleMobileSidebar);
        sidebar.prepend(closeBtn);
      }
    }

    // Adjust controls bar for mobile
    if (controlsBar) {
      // Ensure filter and export buttons are vertically stacked on smaller screens
      const buttonContainer = controlsBar.querySelector(
        ".flex.flex-wrap.items-center.gap-3"
      );
      if (buttonContainer) {
        buttonContainer.classList.add(
          "flex-col",
          "sm:flex-row",
          "items-stretch",
          "sm:items-center"
        );
      }

      // Ensure the filter panel is properly sized on mobile
      const filterPanel = document.getElementById("filter-panel");
      if (filterPanel) {
        filterPanel.classList.add("max-h-[80vh]", "overflow-y-auto");
      }
    }
  }

  /**
   * Disable mobile-specific layout
   */
  function disableMobileLayout() {
    // Hide mobile toggle button
    if (mobileToggleBtn) {
      mobileToggleBtn.classList.add("hidden");
    }

    // Restore map container
    if (mapContainer) {
      mapContainer.classList.remove("col-span-1", "w-full");
    }

    // Restore sidebar
    if (sidebar) {
      // Show sidebar in desktop layout
      sidebar.classList.remove(
        "hidden",
        "fixed",
        "inset-0",
        "z-40",
        "overflow-y-auto"
      );

      // Hide mobile close button
      const closeBtn = sidebar.querySelector(".mobile-close-btn");
      if (closeBtn) {
        closeBtn.classList.add("hidden");
      }
    }

    // Restore controls bar
    if (controlsBar) {
      // Restore horizontal layout for buttons
      const buttonContainer = controlsBar.querySelector(
        ".flex.flex-wrap.items-center.gap-3"
      );
      if (buttonContainer) {
        buttonContainer.classList.remove("flex-col", "items-stretch");
      }

      // Remove mobile-specific classes from filter panel
      const filterPanel = document.getElementById("filter-panel");
      if (filterPanel) {
        filterPanel.classList.remove("max-h-[80vh]");
      }
    }
  }

  /**
   * Toggle sidebar visibility on mobile
   */
  function toggleMobileSidebar() {
    if (!sidebar) return;

    if (sidebar.classList.contains("hidden")) {
      // Show sidebar
      sidebar.classList.remove("hidden");

      // Add backdrop if it doesn't exist
      if (!document.getElementById("mobile-sidebar-backdrop")) {
        const backdrop = document.createElement("div");
        backdrop.id = "mobile-sidebar-backdrop";
        backdrop.className =
          "fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden";
        backdrop.addEventListener("click", toggleMobileSidebar);
        document.body.appendChild(backdrop);
      }

      // Prevent body scrolling
      document.body.classList.add("overflow-hidden");

      // Change toggle button icon
      if (mobileToggleBtn) {
        mobileToggleBtn.innerHTML = '<i class="fas fa-times"></i>';
      }
    } else {
      // Hide sidebar
      sidebar.classList.add("hidden");

      // Remove backdrop
      const backdrop = document.getElementById("mobile-sidebar-backdrop");
      if (backdrop) {
        backdrop.remove();
      }

      // Restore body scrolling
      document.body.classList.remove("overflow-hidden");

      // Change toggle button icon back
      if (mobileToggleBtn) {
        mobileToggleBtn.innerHTML = '<i class="fas fa-info"></i>';
      }
    }
  }
});
