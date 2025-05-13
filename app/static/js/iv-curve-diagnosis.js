/**
 * IV Curve Diagnosis Tool
 *
 * This script provides functionality for IV curve analysis and diagnosis
 * for solar panel performance monitoring. It supports comparing current
 * IV curves with baseline curves to identify potential issues.
 */

document.addEventListener("DOMContentLoaded", function () {
  // DOM elements
  const fileInput = document.getElementById("ivCurveFile");
  const deviceSelect = document.getElementById("deviceSelect");
  const runDiagnosisBtn = document.getElementById("runDiagnosisBtn");
  const diagnosisResult = document.getElementById("diagnosisResult");
  const uploadForm = document.getElementById("uploadForm");
  const sampleDataBtn = document.getElementById("sampleDataBtn");
  const runComparisonBtn = document.getElementById("runComparisonBtn");
  const comparisonChart = document.getElementById("comparisonChart");
  const resetDiagnosisBtn = document.getElementById("resetDiagnosisBtn");
  const simulateBtn = document.getElementById("simulateBtn");

  // Chart references
  let ivCurveChart = null;
  let comparisonChartInstance = null;

  // Initialize select2 if available
  if ($.fn.select2 && deviceSelect) {
    $(deviceSelect).select2({
      placeholder: "Select a device",
      allowClear: true,
    });
  }

  // Load devices for the dropdown
  function loadDevices() {
    if (!deviceSelect) return;

    fetch("/api/devices")
      .then((response) => response.json())
      .then((data) => {
        // Clear previous options
        deviceSelect.innerHTML = '<option value="">Select a device</option>';

        // Add devices to dropdown
        if (data && Array.isArray(data)) {
          data.forEach((device) => {
            const option = document.createElement("option");
            option.value = device.id || device.deviceSn;
            option.textContent = `${device.deviceName || device.deviceSn} (${
              device.deviceType || "Inverter"
            })`;
            deviceSelect.appendChild(option);
          });
        }
      })
      .catch((error) => {
        console.error("Error loading devices:", error);
        // Add fallback mock devices if API fails
        addMockDevices();
      });
  }

  // Add mock devices for testing when API is not available
  function addMockDevices() {
    const mockDevices = [
      { id: "12345", name: "Inverter A-1", type: "Inverter" },
      { id: "54321", name: "Inverter B-2", type: "Inverter" },
      { id: "67890", name: "Inverter C-3", type: "Inverter" },
    ];

    mockDevices.forEach((device) => {
      const option = document.createElement("option");
      option.value = device.id;
      option.textContent = `${device.name} (${device.type})`;
      deviceSelect.appendChild(option);
    });
  }

  // Sample IV curve data for demonstration
  function getSampleData() {
    return {
      voltage: [0, 5, 10, 15, 20, 25, 30, 35, 40, 45],
      current: [9.5, 9.4, 9.3, 9.2, 9.0, 8.5, 7.5, 6.0, 3.5, 0],
      power: [0, 47, 93, 138, 180, 212.5, 225, 210, 140, 0],
    };
  }

  // Create the IV curve chart
  function createIVCurveChart(data) {
    const ctx = document.getElementById("ivCurveChart").getContext("2d");

    // Destroy previous chart if it exists
    if (ivCurveChart) {
      ivCurveChart.destroy();
    }

    ivCurveChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.voltage,
        datasets: [
          {
            label: "Current (A)",
            data: data.current,
            borderColor: "#3B82F6",
            backgroundColor: "rgba(59, 130, 246, 0.1)",
            borderWidth: 2,
            tension: 0.4,
            yAxisID: "y",
          },
          {
            label: "Power (W)",
            data: data.power,
            borderColor: "#10B981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            borderWidth: 2,
            tension: 0.4,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Voltage (V)",
            },
          },
          y: {
            type: "linear",
            display: true,
            position: "left",
            title: {
              display: true,
              text: "Current (A)",
            },
          },
          y1: {
            type: "linear",
            display: true,
            position: "right",
            title: {
              display: true,
              text: "Power (W)",
            },
            grid: {
              drawOnChartArea: false,
            },
          },
        },
      },
    });
  }

  // Create the comparison chart
  function createComparisonChart(currentData, baselineData) {
    const ctx = document.getElementById("comparisonChart").getContext("2d");

    // Destroy previous chart if it exists
    if (comparisonChartInstance) {
      comparisonChartInstance.destroy();
    }

    comparisonChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: currentData.voltage,
        datasets: [
          {
            label: "Current IV Curve",
            data: currentData.current,
            borderColor: "#3B82F6",
            backgroundColor: "rgba(59, 130, 246, 0.1)",
            borderWidth: 2,
            tension: 0.4,
          },
          {
            label: "Baseline IV Curve",
            data: baselineData.current,
            borderColor: "#F59E0B",
            backgroundColor: "rgba(245, 158, 11, 0.1)",
            borderWidth: 2,
            tension: 0.4,
            borderDash: [5, 5],
          },
        ],
      },
      options: {
        responsive: true,
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Voltage (V)",
            },
          },
          y: {
            title: {
              display: true,
              text: "Current (A)",
            },
          },
        },
      },
    });
  }

  // Run IV curve analysis
  function runDiagnosis() {
    // Mock diagnosis results
    const results = analyzeCurve(getSampleData());

    // Display results
    showDiagnosisResults(results);
  }

  // Analyze the IV curve
  function analyzeCurve(data) {
    // Mock analysis - in production this would use advanced algorithms
    // to detect issues based on curve shape, fill factor, etc.

    // Calculate maximum power point
    let maxPower = Math.max(...data.power);
    let maxPowerIndex = data.power.indexOf(maxPower);
    let maxPowerVoltage = data.voltage[maxPowerIndex];
    let maxPowerCurrent = data.current[maxPowerIndex];

    // Calculate fill factor (ratio of actual max power to theoretical max power)
    let theoreticalMaxPower =
      Math.max(...data.current) * Math.max(...data.voltage);
    let fillFactor = maxPower / theoreticalMaxPower;

    // Check for potential issues based on fill factor
    let issues = [];
    let recommendations = [];
    let status = "healthy";

    if (fillFactor < 0.65) {
      status = "critical";
      issues.push("Low fill factor indicating significant performance issues");
      recommendations.push("Inspect panels for physical damage or hot spots");
      recommendations.push("Check for shading issues across the array");
    } else if (fillFactor < 0.75) {
      status = "warning";
      issues.push("Moderate fill factor reduction detected");
      recommendations.push("Clean panels to remove potential dirt or debris");
      recommendations.push(
        "Check string connections for potential loose contacts"
      );
    }

    // Check current curve shape for potential issues
    let currentDropRate =
      (data.current[0] - data.current[data.current.length - 2]) /
      data.current[0];

    if (currentDropRate < 0.5) {
      issues.push("Abnormal current curve shape detected");
      recommendations.push("Check for potential internal panel damage");
      status = status === "healthy" ? "warning" : status;
    }

    return {
      status: status,
      maxPower: maxPower.toFixed(2),
      maxPowerVoltage: maxPowerVoltage.toFixed(1),
      maxPowerCurrent: maxPowerCurrent.toFixed(2),
      fillFactor: (fillFactor * 100).toFixed(1),
      issues: issues,
      recommendations: recommendations,
    };
  }

  // Display diagnosis results
  function showDiagnosisResults(results) {
    if (!diagnosisResult) return;

    // Create result HTML
    let resultHTML = `
      <div class="p-4 rounded-lg ${getStatusClass(results.status)}">
        <div class="flex items-center mb-4">
          <div class="rounded-full p-2 ${getStatusBgClass(
            results.status
          )} mr-3">
            <i class="fas ${getStatusIcon(results.status)} text-white"></i>
          </div>
          <h3 class="text-lg font-semibold">IV Curve Analysis Results</h3>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div class="bg-white p-3 rounded shadow">
            <div class="text-sm text-gray-600">Maximum Power</div>
            <div class="text-xl font-bold">${results.maxPower} W</div>
          </div>
          <div class="bg-white p-3 rounded shadow">
            <div class="text-sm text-gray-600">Fill Factor</div>
            <div class="text-xl font-bold">${results.fillFactor}%</div>
          </div>
          <div class="bg-white p-3 rounded shadow">
            <div class="text-sm text-gray-600">MPP Voltage/Current</div>
            <div class="text-xl font-bold">${results.maxPowerVoltage}V / ${
      results.maxPowerCurrent
    }A</div>
          </div>
        </div>
        
        ${
          results.issues.length > 0
            ? `
          <div class="mb-4">
            <h4 class="font-semibold mb-2">Identified Issues:</h4>
            <ul class="list-disc pl-5">
              ${results.issues.map((issue) => `<li>${issue}</li>`).join("")}
            </ul>
          </div>
        `
            : ""
        }
        
        ${
          results.recommendations.length > 0
            ? `
          <div>
            <h4 class="font-semibold mb-2">Recommendations:</h4>
            <ul class="list-disc pl-5">
              ${results.recommendations
                .map((rec) => `<li>${rec}</li>`)
                .join("")}
            </ul>
          </div>
        `
            : ""
        }
      </div>
    `;

    // Add result to the page
    diagnosisResult.innerHTML = resultHTML;
    diagnosisResult.classList.remove("hidden");
  }

  // Helper functions for status styling
  function getStatusClass(status) {
    switch (status) {
      case "critical":
        return "bg-red-50 border border-red-200";
      case "warning":
        return "bg-amber-50 border border-amber-200";
      default:
        return "bg-green-50 border border-green-200";
    }
  }

  function getStatusBgClass(status) {
    switch (status) {
      case "critical":
        return "bg-red-500";
      case "warning":
        return "bg-amber-500";
      default:
        return "bg-green-500";
    }
  }

  function getStatusIcon(status) {
    switch (status) {
      case "critical":
        return "fa-exclamation-triangle";
      case "warning":
        return "fa-exclamation-circle";
      default:
        return "fa-check-circle";
    }
  }

  // Generate slightly different baseline data for comparison
  function getBaselineData(current) {
    const baselineData = JSON.parse(JSON.stringify(current)); // Clone current data

    // Modify the current values slightly to represent ideal conditions
    baselineData.current = baselineData.current.map(
      (val) => val * (1 + Math.random() * 0.1)
    );

    // Recalculate power
    baselineData.power = baselineData.voltage.map(
      (v, i) => v * baselineData.current[i]
    );

    return baselineData;
  }

  // Event listeners
  if (loadDevices) {
    loadDevices();
  }

  if (sampleDataBtn) {
    sampleDataBtn.addEventListener("click", function () {
      const sampleData = getSampleData();
      createIVCurveChart(sampleData);
    });
  }

  if (runDiagnosisBtn) {
    runDiagnosisBtn.addEventListener("click", runDiagnosis);
  }

  if (runComparisonBtn) {
    runComparisonBtn.addEventListener("click", function () {
      const currentData = getSampleData();
      const baselineData = getBaselineData(currentData);
      createComparisonChart(currentData, baselineData);
    });
  }

  if (resetDiagnosisBtn) {
    resetDiagnosisBtn.addEventListener("click", function () {
      if (diagnosisResult) {
        diagnosisResult.classList.add("hidden");
      }

      if (ivCurveChart) {
        ivCurveChart.destroy();
        ivCurveChart = null;
      }

      if (comparisonChartInstance) {
        comparisonChartInstance.destroy();
        comparisonChartInstance = null;
      }

      if (fileInput) {
        fileInput.value = "";
      }

      if (deviceSelect) {
        deviceSelect.value = "";
        if ($.fn.select2) {
          $(deviceSelect).trigger("change");
        }
      }
    });
  }

  // Initialize with sample data
  if (document.getElementById("ivCurveChart")) {
    createIVCurveChart(getSampleData());
  }
});
