// Operations App JavaScript for managing operations and scheduled jobs

/**
 * Main Operations App
 * Handles navigation and common functionality
 */
const operationsApp = {
  activeTab: "dashboard",
  isLoading: false,
  hasError: false,
  errorMessage: "",

  // Initialize the operations app
  init() {
    console.log("Initializing operations app");
    this.activeTab = "dashboard";
    this.refreshOperationsData();
  },

  // Refresh operations data
  refreshOperationsData() {
    this.isLoading = true;

    // Here you would typically fetch the latest operations data
    // We're simulating a fetch with a timeout
    setTimeout(() => {
      this.isLoading = false;
    }, 500);
  },

  // Generate operations report
  generateOperationsReport() {
    alert("Generating operations report...");
    // This would make a server request to generate a report
  },
};

/**
 * Scheduler Management Component
 * Handles all operations related to APScheduler jobs
 */
const schedulerManager = {
  jobs: [],
  isLoading: false,
  error: null,

  // Initialize the scheduler component
  initScheduler() {
    console.log("Initializing scheduler component");
    this.loadJobs();
  },

  // Load all scheduled jobs
  loadJobs() {
    this.isLoading = true;

    fetch("/api/scheduler/jobs")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load jobs");
        }
        return response.json();
      })
      .then((data) => {
        this.jobs = data.jobs || [];
        this.isLoading = false;
      })
      .catch((error) => {
        console.error("Error loading jobs:", error);
        this.error = error.message;
        this.isLoading = false;
      });
  },

  // Add an interval job
  addIntervalJob(event) {
    event.preventDefault();
    const form = event.target;

    const jobData = {
      job_id: form.elements.job_id.value || undefined,
      name: form.elements.name.value,
      func: form.elements.func.value,
      description: form.elements.description.value || undefined,
    };

    // Add interval parameters
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
        alert("Invalid JSON format for arguments");
        return;
      }
    }

    // Add keyword arguments if provided
    if (form.elements.kwargs.value) {
      try {
        jobData.kwargs = JSON.parse(form.elements.kwargs.value);
      } catch (e) {
        alert("Invalid JSON format for keyword arguments");
        return;
      }
    }

    fetch("/api/scheduler/interval-job", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jobData),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          form.reset();
          this.loadJobs();
          alert("Interval job added successfully");
        } else {
          alert(data.message || "Failed to add interval job");
        }
      })
      .catch((error) => {
        console.error("Error adding interval job:", error);
        alert("Failed to add interval job");
      });
  },

  // Add a cron job
  addCronJob(event) {
    event.preventDefault();
    const form = event.target;

    const jobData = {
      job_id: form.elements.job_id.value || undefined,
      name: form.elements.name.value,
      func: form.elements.func.value,
      cron_expression: form.elements.cron_expression.value,
      description: form.elements.description.value || undefined,
    };

    // Add arguments if provided
    if (form.elements.args.value) {
      try {
        jobData.args = JSON.parse(form.elements.args.value);
      } catch (e) {
        alert("Invalid JSON format for arguments");
        return;
      }
    }

    // Add keyword arguments if provided
    if (form.elements.kwargs.value) {
      try {
        jobData.kwargs = JSON.parse(form.elements.kwargs.value);
      } catch (e) {
        alert("Invalid JSON format for keyword arguments");
        return;
      }
    }

    fetch("/api/scheduler/cron-job", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jobData),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          form.reset();
          this.loadJobs();
          alert("Cron job added successfully");
        } else {
          alert(data.message || "Failed to add cron job");
        }
      })
      .catch((error) => {
        console.error("Error adding cron job:", error);
        alert("Failed to add cron job");
      });
  },

  // Add a date (one-time) job
  addDateJob(event) {
    event.preventDefault();
    const form = event.target;

    const jobData = {
      job_id: form.elements.job_id.value || undefined,
      name: form.elements.name.value,
      func: form.elements.func.value,
      run_date: form.elements.run_date.value,
      description: form.elements.description.value || undefined,
    };

    // Add arguments if provided
    if (form.elements.args.value) {
      try {
        jobData.args = JSON.parse(form.elements.args.value);
      } catch (e) {
        alert("Invalid JSON format for arguments");
        return;
      }
    }

    // Add keyword arguments if provided
    if (form.elements.kwargs.value) {
      try {
        jobData.kwargs = JSON.parse(form.elements.kwargs.value);
      } catch (e) {
        alert("Invalid JSON format for keyword arguments");
        return;
      }
    }

    fetch("/api/scheduler/date-job", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jobData),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          form.reset();
          this.loadJobs();
          alert("One-time job added successfully");
        } else {
          alert(data.message || "Failed to add one-time job");
        }
      })
      .catch((error) => {
        console.error("Error adding one-time job:", error);
        alert("Failed to add one-time job");
      });
  },

  // Remove a job
  removeJob(jobId) {
    if (!confirm(`Are you sure you want to remove job "${jobId}"?`)) {
      return;
    }

    fetch(`/api/scheduler/jobs/${jobId}`, {
      method: "DELETE",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          this.loadJobs();
          alert("Job removed successfully");
        } else {
          alert(data.message || "Failed to remove job");
        }
      })
      .catch((error) => {
        console.error("Error removing job:", error);
        alert("Failed to remove job");
      });
  },

  // Pause a job
  pauseJob(jobId) {
    fetch(`/api/scheduler/jobs/${jobId}/pause`, {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          this.loadJobs();
          alert("Job paused successfully");
        } else {
          alert(data.message || "Failed to pause job");
        }
      })
      .catch((error) => {
        console.error("Error pausing job:", error);
        alert("Failed to pause job");
      });
  },

  // Resume a job
  resumeJob(jobId) {
    fetch(`/api/scheduler/jobs/${jobId}/resume`, {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          this.loadJobs();
          alert("Job resumed successfully");
        } else {
          alert(data.message || "Failed to resume job");
        }
      })
      .catch((error) => {
        console.error("Error resuming job:", error);
        alert("Failed to resume job");
      });
  },

  // Run a job immediately
  runJob(jobId) {
    fetch(`/api/scheduler/jobs/${jobId}/run`, {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          alert("Job triggered successfully");
        } else {
          alert(data.message || "Failed to run job");
        }
      })
      .catch((error) => {
        console.error("Error running job:", error);
        alert("Failed to run job");
      });
  },

  // Set up default monitoring jobs
  setupDefaultJobs() {
    if (
      !confirm("Are you sure you want to set up the default monitoring jobs?")
    ) {
      return;
    }

    fetch("/api/scheduler/setup-default-jobs", {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          this.loadJobs();
          alert("Default monitoring jobs set up successfully");
        } else {
          alert(data.message || "Failed to set up default jobs");
        }
      })
      .catch((error) => {
        console.error("Error setting up default jobs:", error);
        alert("Failed to set up default jobs");
      });
  },
};
