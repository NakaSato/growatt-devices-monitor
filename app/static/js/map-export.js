/**
 * Map Export Functions - For exporting and printing map data
 * Provides functionality to export plant data and print map views
 */

document.addEventListener("DOMContentLoaded", function () {
  // Export button
  const exportBtn = document.getElementById("export-btn");

  if (exportBtn) {
    // Initialize export dropdown
    initializeExportDropdown();

    // Add click event to export button to toggle dropdown
    exportBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      const dropdown = document.getElementById("export-options");
      dropdown.classList.toggle("hidden");
    });

    // Close dropdown when clicking elsewhere
    document.addEventListener("click", function () {
      const dropdown = document.getElementById("export-options");
      if (dropdown && !dropdown.classList.contains("hidden")) {
        dropdown.classList.add("hidden");
      }
    });
  }

  // Initialize event listeners for export actions
  function initializeExportDropdown() {
    // Get export option elements
    const exportCsvBtn = document.getElementById("export-csv");
    const exportPdfBtn = document.getElementById("export-pdf");
    const printMapBtn = document.getElementById("print-map");

    // Add event listeners to export options
    if (exportCsvBtn) {
      exportCsvBtn.addEventListener("click", exportAsCSV);
    }

    if (exportPdfBtn) {
      exportPdfBtn.addEventListener("click", exportAsPDF);
    }

    if (printMapBtn) {
      printMapBtn.addEventListener("click", printMap);
    }
  }

  // Export plant data as CSV
  function exportAsCSV() {
    if (!window.solarPlantsData || window.solarPlantsData.length === 0) {
      showNotification("No data available to export", "error");
      return;
    }

    // Define CSV headers
    const headers = [
      "ID",
      "Name",
      "Status",
      "Capacity (kW)",
      "Current Output (kW)",
      "Today's Energy (kWh)",
      "Peak Output (kW)",
      "Installation Date",
      "Location",
      "Latitude",
      "Longitude",
    ];

    // Convert plant data to CSV format
    let csvContent = headers.join(",") + "\n";

    // Get filtered plants data if filtering is active
    const plants = getFilteredPlantsData();

    // Add each plant as a row in CSV
    plants.forEach((plant) => {
      const row = [
        plant.id,
        `"${plant.name}"`, // Wrap name in quotes to handle commas
        plant.status,
        plant.capacity,
        plant.currentOutput,
        plant.todayEnergy,
        plant.peakOutput,
        plant.installDate,
        `"${plant.location}"`, // Wrap location in quotes to handle commas
        plant.latitude,
        plant.longitude,
      ];

      csvContent += row.join(",") + "\n";
    });

    // Create a downloadable link for the CSV
    const encodedUri = encodeURI("data:text/csv;charset=utf-8," + csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `solar_plants_data_${formatDate(new Date())}.csv`
    );
    document.body.appendChild(link);

    // Trigger download and remove link
    link.click();
    document.body.removeChild(link);

    // Show success notification
    showNotification("CSV file exported successfully", "success");

    // Hide dropdown
    document.getElementById("export-options").classList.add("hidden");
  }

  // Export map data as PDF
  function exportAsPDF() {
    showNotification("Preparing PDF export...", "info");

    // Prepare data for PDF export
    const data = {
      date: formatDate(new Date()),
      totalPlants: window.solarPlantsData ? window.solarPlantsData.length : 0,
      filteredPlants: getFilteredPlantsData().length,
      plants: getFilteredPlantsData(),
    };

    // In a real app, this would call a server-side endpoint to generate the PDF
    // For this example, we'll simulate the PDF generation with a timeout
    setTimeout(() => {
      showNotification("PDF export generated successfully", "success");

      // Simulate PDF download by creating a fake link
      const link = document.createElement("a");
      link.setAttribute("href", "#");
      link.setAttribute(
        "download",
        `solar_plants_report_${formatDate(new Date())}.pdf`
      );
      document.body.appendChild(link);

      // Hide dropdown
      document.getElementById("export-options").classList.add("hidden");

      // Show modal with "PDF would be generated here" message
      showExportModal(
        "PDF Export",
        "In a production environment, this would generate a PDF with plant data and map snapshot. " +
          "The PDF would include filtered plants data, performance metrics, and current map view."
      );
    }, 1500);
  }

  // Print current map view
  function printMap() {
    showNotification("Preparing map for printing...", "info");

    // Hide dropdown
    document.getElementById("export-options").classList.add("hidden");

    // Store current map state
    const mapContainer = document.querySelector(".lg\\:col-span-3");
    const originalClasses = mapContainer.className;
    const sidebar = document.querySelector(".lg\\:col-span-1");
    const controls = document.querySelectorAll(".absolute");

    // Hide controls and sidebar for print
    controls.forEach((control) => {
      if (!control.classList.contains("print-include")) {
        control.style.display = "none";
      }
    });

    if (sidebar) {
      sidebar.style.display = "none";
    }

    // Optimize map for printing
    mapContainer.className = "w-full h-[800px] print:w-full print:h-full";

    // Add print title
    const printTitle = document.createElement("div");
    printTitle.className = "print-only text-center mb-4";
    printTitle.innerHTML = `
      <h1 class="text-2xl font-bold">Solar Plants Map</h1>
      <p class="text-sm text-gray-600">Generated on ${formatDate(
        new Date()
      )}</p>
    `;
    mapContainer.parentNode.insertBefore(printTitle, mapContainer);

    // Add print stylesheet if it doesn't exist
    if (!document.getElementById("print-stylesheet")) {
      const style = document.createElement("style");
      style.id = "print-stylesheet";
      style.textContent = `
        @media print {
          body * {
            visibility: hidden;
          }
          .print-only, .print-only * {
            visibility: visible;
          }
          #thailand-map-container, #leaflet-map-container, 
          #thailand-map-container *, #leaflet-map-container * {
            visibility: visible;
          }
          .container {
            width: 100%;
            max-width: 100%;
            padding: 0;
            margin: 0;
          }
          .print-only {
            display: block !important;
            visibility: visible !important;
          }
          @page {
            size: landscape;
            margin: 1cm;
          }
        }
      `;
      document.head.appendChild(style);
    }

    // Trigger browser print dialog
    setTimeout(() => {
      window.print();

      // Restore original state after print dialog closes
      setTimeout(() => {
        // Remove print title
        if (printTitle && printTitle.parentNode) {
          printTitle.parentNode.removeChild(printTitle);
        }

        // Restore map container
        mapContainer.className = originalClasses;

        // Show controls and sidebar
        controls.forEach((control) => {
          control.style.display = "";
        });

        if (sidebar) {
          sidebar.style.display = "";
        }

        showNotification("Map printed successfully", "success");
      }, 1000);
    }, 500);
  }

  // Helper function to show notification
  function showNotification(message, type = "info") {
    // Create notification element if it doesn't exist
    let notification = document.getElementById("notification");
    if (!notification) {
      notification = document.createElement("div");
      notification.id = "notification";
      notification.className =
        "fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 translate-y-20 opacity-0 z-50";
      document.body.appendChild(notification);
    }

    // Set notification type
    notification.className =
      "fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 z-50";

    // Add color based on type
    switch (type) {
      case "success":
        notification.className += " bg-green-500 text-white";
        break;
      case "error":
        notification.className += " bg-red-500 text-white";
        break;
      case "warning":
        notification.className += " bg-yellow-500 text-white";
        break;
      default:
        notification.className += " bg-blue-500 text-white";
    }

    // Set message
    notification.textContent = message;

    // Show notification
    setTimeout(() => {
      notification.classList.remove("translate-y-20", "opacity-0");
    }, 100);

    // Hide notification after 3 seconds
    setTimeout(() => {
      notification.classList.add("translate-y-20", "opacity-0");
    }, 3000);
  }

  // Helper function to show modal
  function showExportModal(title, content) {
    // Create modal if it doesn't exist
    let modal = document.getElementById("export-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "export-modal";
      modal.className =
        "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 opacity-0 pointer-events-none transition-opacity duration-300";
      modal.innerHTML = `
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transform transition-transform duration-300 scale-95">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white" id="modal-title"></h3>
            <button id="close-modal" class="text-gray-400 hover:text-gray-500 focus:outline-none">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="mt-3" id="modal-content"></div>
          <div class="mt-5 flex justify-end">
            <button id="modal-ok" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
              OK
            </button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      // Add event listeners to close modal
      document
        .getElementById("close-modal")
        .addEventListener("click", closeModal);
      document.getElementById("modal-ok").addEventListener("click", closeModal);
      modal.addEventListener("click", function (e) {
        if (e.target === this) closeModal();
      });
    }

    // Set modal content
    document.getElementById("modal-title").textContent = title;
    document.getElementById("modal-content").innerHTML = content;

    // Show modal
    modal.classList.remove("opacity-0", "pointer-events-none");
    setTimeout(() => {
      modal.querySelector("div").classList.remove("scale-95");
      modal.querySelector("div").classList.add("scale-100");
    }, 100);

    // Function to close modal
    function closeModal() {
      const modalElement = document.getElementById("export-modal");
      modalElement.querySelector("div").classList.remove("scale-100");
      modalElement.querySelector("div").classList.add("scale-95");
      setTimeout(() => {
        modalElement.classList.add("opacity-0", "pointer-events-none");
      }, 100);
    }
  }

  // Helper function to get filtered plants data
  function getFilteredPlantsData() {
    // If window.filteredPlantsData exists (set by filter functions), use it
    // Otherwise use all plants data
    return window.filteredPlantsData || window.solarPlantsData || [];
  }

  // Helper function to format date as YYYY-MM-DD
  function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }
});
