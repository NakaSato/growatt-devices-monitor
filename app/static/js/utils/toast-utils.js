/**
 * Toast Notification Utility
 * Provides simple toast notifications for various operations
 */

// Create a toast container element if it doesn't exist
function getOrCreateToastContainer() {
  let container = document.getElementById("toast-container");

  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className =
      "fixed top-0 right-0 p-4 z-50 flex flex-col items-end space-y-2";
    document.body.appendChild(container);
  }

  return container;
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, warning, info)
 * @param {number} duration - How long to show the toast in ms
 */
window.showToast = function (message, type = "success", duration = 3000) {
  const container = getOrCreateToastContainer();

  // Create toast element
  const toast = document.createElement("div");

  // Set base classes
  toast.className =
    "toast-notification flex items-center p-3 rounded-lg shadow-lg transform transition-all duration-300 ease-in-out translate-x-full";

  // Add type-specific classes
  const typeClasses = {
    success: "bg-green-100 border-l-4 border-green-600 text-green-800",
    error: "bg-red-100 border-l-4 border-red-600 text-red-800",
    warning: "bg-yellow-100 border-l-4 border-yellow-600 text-yellow-800",
    info: "bg-blue-100 border-l-4 border-blue-600 text-blue-800",
  };

  toast.className += " " + (typeClasses[type] || typeClasses.info);

  // Create icon based on type
  const iconSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  iconSvg.setAttribute("class", "h-5 w-5 mr-2 flex-shrink-0");
  iconSvg.setAttribute("fill", "none");
  iconSvg.setAttribute("viewBox", "0 0 24 24");
  iconSvg.setAttribute("stroke", "currentColor");

  const iconPath = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "path"
  );
  iconPath.setAttribute("stroke-linecap", "round");
  iconPath.setAttribute("stroke-linejoin", "round");
  iconPath.setAttribute("stroke-width", "2");

  // Different path for each type
  switch (type) {
    case "success":
      iconPath.setAttribute("d", "M5 13l4 4L19 7");
      break;
    case "error":
      iconPath.setAttribute("d", "M6 18L18 6M6 6l12 12");
      break;
    case "warning":
      iconPath.setAttribute(
        "d",
        "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      );
      break;
    default: // info
      iconPath.setAttribute(
        "d",
        "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      );
  }

  iconSvg.appendChild(iconPath);
  toast.appendChild(iconSvg);

  // Create message element
  const messageSpan = document.createElement("span");
  messageSpan.className = "text-sm font-medium";
  messageSpan.textContent = message;
  toast.appendChild(messageSpan);

  // Add close button
  const closeButton = document.createElement("button");
  closeButton.className =
    "ml-auto -mr-1 text-gray-600 hover:text-gray-800 focus:outline-none";
  closeButton.innerHTML =
    '<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>';
  closeButton.addEventListener("click", () => {
    removeToast(toast);
  });
  toast.appendChild(closeButton);

  // Add to container
  container.appendChild(toast);

  // Animation to slide in
  setTimeout(() => {
    toast.classList.remove("translate-x-full");
  }, 10);

  // Set timeout to remove
  const timeoutId = setTimeout(() => {
    removeToast(toast);
  }, duration);

  // Store timeout ID on the element
  toast.dataset.timeoutId = timeoutId;

  return toast;
};

/**
 * Remove a toast notification with animation
 * @param {HTMLElement} toast - The toast element to remove
 */
function removeToast(toast) {
  // Clear the timeout if it exists
  const timeoutId = toast.dataset.timeoutId;
  if (timeoutId) {
    clearTimeout(parseInt(timeoutId));
  }

  // Animate out
  toast.classList.add("translate-x-full");

  // Remove after animation
  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }

    // If no more toasts, remove the container
    const container = document.getElementById("toast-container");
    if (container && container.children.length === 0) {
      document.body.removeChild(container);
    }
  }, 300);
}

/**
 * Show a success toast
 * @param {string} message - The message to display
 * @param {number} duration - How long to show the toast in ms
 */
window.showSuccessToast = function (message, duration = 3000) {
  return window.showToast(message, "success", duration);
};

/**
 * Show an error toast
 * @param {string} message - The message to display
 * @param {number} duration - How long to show the toast in ms
 */
window.showErrorToast = function (message, duration = 5000) {
  return window.showToast(message, "error", duration);
};

/**
 * Show a warning toast
 * @param {string} message - The message to display
 * @param {number} duration - How long to show the toast in ms
 */
window.showWarningToast = function (message, duration = 4000) {
  return window.showToast(message, "warning", duration);
};

/**
 * Show an info toast
 * @param {string} message - The message to display
 * @param {number} duration - How long to show the toast in ms
 */
window.showInfoToast = function (message, duration = 3000) {
  return window.showToast(message, "info", duration);
};
