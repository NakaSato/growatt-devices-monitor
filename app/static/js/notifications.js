/**
 * Global Notification System
 * Provides a unified notification system for the application
 */

document.addEventListener("DOMContentLoaded", function () {
  // Create a container for notifications if it doesn't exist
  if (!document.getElementById("notification-container")) {
    const notificationContainer = document.createElement("div");
    notificationContainer.id = "notification-container";
    notificationContainer.className =
      "fixed bottom-4 right-4 z-50 flex flex-col space-y-2";
    document.body.appendChild(notificationContainer);
  }

  /**
   * Show a notification
   * @param {string} message - The notification message
   * @param {string} type - The type of notification (success, error, warning, info)
   * @param {number} duration - How long to show the notification in ms
   */
  window.showNotification = function (message, type = "info", duration = 3000) {
    const container = document.getElementById("notification-container");
    if (!container) return;

    // Create notification element
    const notification = document.createElement("div");
    notification.className = `px-4 py-2 rounded-lg shadow-lg max-w-xs transform transition-all duration-300 flex items-center space-x-2 notification-${type}`;

    // Set background color based on type
    switch (type) {
      case "success":
        notification.classList.add("bg-green-500", "text-white");
        break;
      case "error":
        notification.classList.add("bg-red-500", "text-white");
        break;
      case "warning":
        notification.classList.add("bg-yellow-500", "text-white");
        break;
      default:
        notification.classList.add("bg-blue-500", "text-white");
    }

    // Add icon based on type
    let icon;
    switch (type) {
      case "success":
        icon = "check-circle";
        break;
      case "error":
        icon = "exclamation-circle";
        break;
      case "warning":
        icon = "exclamation-triangle";
        break;
      default:
        icon = "info-circle";
    }

    // Set content
    notification.innerHTML = `
      <div class="flex-shrink-0">
        <i class="fas fa-${icon}"></i>
      </div>
      <div class="flex-1">
        ${message}
      </div>
    `;

    // Add to container
    container.appendChild(notification);

    // Animate in
    setTimeout(() => {
      notification.classList.add("translate-y-0", "opacity-100");
    }, 10);

    // Remove after duration
    setTimeout(() => {
      notification.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => {
        notification.remove();
      }, 300);
    }, duration);

    return notification;
  };
});
