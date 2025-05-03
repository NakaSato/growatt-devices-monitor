// Operations App JavaScript for managing scheduled jobs

/**
 * Scheduler Management Module
 * Handles all operations related to APScheduler jobs
 */
const schedulerApp = {
  jobs: [],

  // Initialize the scheduler app
  init: function () {
    console.log("Initializing scheduler app");
    this.loadJobs();
    this.setupEventListeners();
  },

  // Load all scheduled jobs
  loadJobs: function () {
    fetch("/api/scheduler/jobs")
      .then((response) => response.json())
      .then((data) => {
        this.jobs = data.jobs || [];
        this.renderJobsTable();
      })
      .catch((error) => {
        console.error("Error loading jobs:", error);
        showToast("error", "Failed to load scheduled jobs");
      });
  },

  // Set up all event listeners
  setupEventListeners: function () {
    // Form submissions
    document
      .getElementById("intervalJobForm")
      ?.addEventListener("submit", this.handleIntervalJobSubmit.bind(this));
    document
      .getElementById("cronJobForm")
      ?.addEventListener("submit", this.handleCronJobSubmit.bind(this));
    document
      .getElementById("dateJobForm")
      ?.addEventListener("submit", this.handleDateJobSubmit.bind(this));

    // Default jobs setup
    document
      .getElementById("setupDefaultJobs")
      ?.addEventListener("click", this.handleSetupDefaultJobs.bind(this));

    // Tab switching
    const tabButtons = document.querySelectorAll(".job-tab-btn");
    tabButtons.forEach((button) => {
      button.addEventListener("click", function () {
        // Remove active class from all buttons
        tabButtons.forEach((btn) => btn.classList.remove("active"));

        // Add active class to clicked button
        this.classList.add("active");

        // Hide all tab content
        document.querySelectorAll(".job-tab-content").forEach((content) => {
          content.style.display = "none";
        });

        // Show relevant tab content
        const tabId = this.getAttribute("data-tab");
        document.getElementById(tabId).style.display = "block";
      });
    });
  },

  // Render jobs table with current data
  renderJobsTable: function () {
    const tableBody = document.getElementById("jobsTableBody");
    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (this.jobs.length === 0) {
      const row = document.createElement("tr");
      row.innerHTML = `<td colspan="7" class="text-center">No scheduled jobs found</td>`;
      tableBody.appendChild(row);
      return;
    }

    this.jobs.forEach((job) => {
      const row = document.createElement("tr");

      // Format next run time
      let nextRunTime = "Not scheduled";
      if (job.next_run_time) {
        const date = new Date(job.next_run_time);
        nextRunTime = date.toLocaleString();
      }

      // Determine job type icon
      let typeIcon = "";
      switch (job.type) {
        case "interval":
          typeIcon = '<i class="fas fa-redo" title="Interval Job"></i>';
          break;
        case "cron":
          typeIcon = '<i class="fas fa-calendar-alt" title="Cron Job"></i>';
          break;
        case "date":
          typeIcon = '<i class="fas fa-clock" title="One-time Job"></i>';
          break;
        default:
          typeIcon = '<i class="fas fa-question" title="Unknown Job Type"></i>';
      }

      row.innerHTML = `
                <td>${job.id}</td>
                <td>${job.name || "<em>Unnamed</em>"}</td>
                <td>${typeIcon} ${job.type}</td>
                <td class="text-truncate" style="max-width: 200px;" title="${
                  job.func
                }">${job.func}</td>
                <td>${job.description || "<em>No description</em>"}</td>
                <td>${nextRunTime}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-primary run-job" data-id="${
                          job.id
                        }" title="Run Now">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-warning pause-job" data-id="${
                          job.id
                        }" title="Pause Job">
                            <i class="fas fa-pause"></i>
                        </button>
                        <button class="btn btn-success resume-job" data-id="${
                          job.id
                        }" title="Resume Job">
                            <i class="fas fa-sync"></i>
                        </button>
                        <button class="btn btn-danger remove-job" data-id="${
                          job.id
                        }" title="Remove Job">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;

      tableBody.appendChild(row);
    });

    // Add event listeners to job action buttons
    this.setupJobActionButtons();
  },

  // Set up event listeners for job action buttons
  setupJobActionButtons: function () {
    // Run job buttons
    document.querySelectorAll(".run-job").forEach((button) => {
      button.addEventListener("click", (event) => {
        const jobId = event.currentTarget.getAttribute("data-id");
        this.runJob(jobId);
      });
    });

    // Pause job buttons
    document.querySelectorAll(".pause-job").forEach((button) => {
      button.addEventListener("click", (event) => {
        const jobId = event.currentTarget.getAttribute("data-id");
        this.pauseJob(jobId);
      });
    });

    // Resume job buttons
    document.querySelectorAll(".resume-job").forEach((button) => {
      button.addEventListener("click", (event) => {
        const jobId = event.currentTarget.getAttribute("data-id");
        this.resumeJob(jobId);
      });
    });

    // Remove job buttons
    document.querySelectorAll(".remove-job").forEach((button) => {
      button.addEventListener("click", (event) => {
        const jobId = event.currentTarget.getAttribute("data-id");
        if (confirm(`Are you sure you want to remove job "${jobId}"?`)) {
          this.removeJob(jobId);
        }
      });
    });
  },

  // Handle form submission for interval jobs
  handleIntervalJobSubmit: function (event) {
    event.preventDefault();
    const form = event.target;

    const jobData = {
      job_id: form.elements.jobId.value,
      func: form.elements.func.value,
      description: form.elements.description.value,
    };

    // Add interval parameters if provided
    if (form.elements.seconds.value) {
      jobData.seconds = parseInt(form.elements.seconds.value, 10);
    }
    if (form.elements.minutes.value) {
      jobData.minutes = parseInt(form.elements.minutes.value, 10);
    }
    if (form.elements.hours.value) {
      jobData.hours = parseInt(form.elements.hours.value, 10);
    }

    // Add arguments if provided
    if (form.elements.args.value) {
      try {
        jobData.args = JSON.parse(form.elements.args.value);
      } catch (e) {
        showToast("error", "Invalid JSON format for arguments");
        return;
      }
    }

    // Add keyword arguments if provided
    if (form.elements.kwargs.value) {
      try {
        jobData.kwargs = JSON.parse(form.elements.kwargs.value);
      } catch (e) {
        showToast("error", "Invalid JSON format for keyword arguments");
        return;
      }
    }

    this.addIntervalJob(jobData);
  },

  // Handle form submission for cron jobs
  handleCronJobSubmit: function (event) {
    event.preventDefault();
    const form = event.target;

    const jobData = {
      job_id: form.elements.jobId.value,
      func: form.elements.func.value,
      cron: form.elements.cron.value,
      description: form.elements.description.value,
    };

    // Add arguments if provided
    if (form.elements.args.value) {
      try {
        jobData.args = JSON.parse(form.elements.args.value);
      } catch (e) {
        showToast("error", "Invalid JSON format for arguments");
        return;
      }
    }

    // Add keyword arguments if provided
    if (form.elements.kwargs.value) {
      try {
        jobData.kwargs = JSON.parse(form.elements.kwargs.value);
      } catch (e) {
        showToast("error", "Invalid JSON format for keyword arguments");
        return;
      }
    }

    this.addCronJob(jobData);
  },

  // Handle form submission for date jobs
  handleDateJobSubmit: function (event) {
    event.preventDefault();
    const form = event.target;

    const jobData = {
      job_id: form.elements.jobId.value,
      func: form.elements.func.value,
      run_date: form.elements.runDate.value,
      description: form.elements.description.value,
    };

    // Add arguments if provided
    if (form.elements.args.value) {
      try {
        jobData.args = JSON.parse(form.elements.args.value);
      } catch (e) {
        showToast("error", "Invalid JSON format for arguments");
        return;
      }
    }

    // Add keyword arguments if provided
    if (form.elements.kwargs.value) {
      try {
        jobData.kwargs = JSON.parse(form.elements.kwargs.value);
      } catch (e) {
        showToast("error", "Invalid JSON format for keyword arguments");
        return;
      }
    }

    this.addDateJob(jobData);
  },

  // Add an interval job
  addIntervalJob: function (jobData) {
    fetch("/api/scheduler/interval-job", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jobData),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.job_id) {
          showToast("success", "Interval job added successfully");
          // Reset form and reload jobs
          document.getElementById("intervalJobForm").reset();
          this.loadJobs();
        } else {
          showToast("error", data.message || "Failed to add interval job");
        }
      })
      .catch((error) => {
        console.error("Error adding interval job:", error);
        showToast("error", "Failed to add interval job");
      });
  },

  // Add a cron job
  addCronJob: function (jobData) {
    fetch("/api/scheduler/cron-job", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jobData),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.job_id) {
          showToast("success", "Cron job added successfully");
          // Reset form and reload jobs
          document.getElementById("cronJobForm").reset();
          this.loadJobs();
        } else {
          showToast("error", data.message || "Failed to add cron job");
        }
      })
      .catch((error) => {
        console.error("Error adding cron job:", error);
        showToast("error", "Failed to add cron job");
      });
  },

  // Add a date job
  addDateJob: function (jobData) {
    fetch("/api/scheduler/date-job", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jobData),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.job_id) {
          showToast("success", "One-time job added successfully");
          // Reset form and reload jobs
          document.getElementById("dateJobForm").reset();
          this.loadJobs();
        } else {
          showToast("error", data.message || "Failed to add one-time job");
        }
      })
      .catch((error) => {
        console.error("Error adding one-time job:", error);
        showToast("error", "Failed to add one-time job");
      });
  },

  // Remove a job
  removeJob: function (jobId) {
    fetch(`/api/scheduler/jobs/${jobId}`, {
      method: "DELETE",
    })
      .then((response) => response.json())
      .then((data) => {
        showToast("success", data.message || "Job removed successfully");
        this.loadJobs();
      })
      .catch((error) => {
        console.error("Error removing job:", error);
        showToast("error", "Failed to remove job");
      });
  },

  // Pause a job
  pauseJob: function (jobId) {
    fetch(`/api/scheduler/jobs/${jobId}/pause`, {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        showToast("success", data.message || "Job paused successfully");
        this.loadJobs();
      })
      .catch((error) => {
        console.error("Error pausing job:", error);
        showToast("error", "Failed to pause job");
      });
  },

  // Resume a job
  resumeJob: function (jobId) {
    fetch(`/api/scheduler/jobs/${jobId}/resume`, {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        showToast("success", data.message || "Job resumed successfully");
        this.loadJobs();
      })
      .catch((error) => {
        console.error("Error resuming job:", error);
        showToast("error", "Failed to resume job");
      });
  },

  // Run a job immediately
  runJob: function (jobId) {
    fetch(`/api/scheduler/jobs/${jobId}/run`, {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        showToast("success", data.message || "Job triggered successfully");
      })
      .catch((error) => {
        console.error("Error running job:", error);
        showToast("error", "Failed to run job");
      });
  },

  // Set up default jobs
  handleSetupDefaultJobs: function () {
    if (
      confirm("Are you sure you want to set up the default monitoring jobs?")
    ) {
      fetch("/api/scheduler/setup-jobs", {
        method: "POST",
      })
        .then((response) => response.json())
        .then((data) => {
          showToast(
            "success",
            data.message || "Default jobs set up successfully"
          );
          this.loadJobs();
        })
        .catch((error) => {
          console.error("Error setting up default jobs:", error);
          showToast("error", "Failed to set up default jobs");
        });
    }
  },
};

/**
 * Helper function to show toast notifications
 */
function showToast(type, message) {
  // Check if toastr is available
  if (typeof toastr !== "undefined") {
    toastr[type](message);
  } else {
    // Fallback to alert
    alert(message);
  }
}

// Initialize scheduler app when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("scheduler-management")) {
    schedulerApp.init();
  }
});
