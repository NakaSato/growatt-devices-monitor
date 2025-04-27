#!/bin/bash
# Enhanced wrapper script to run data_sync.py with proper environment

# -----------------------------------------------------
# Configuration (can be overridden by config file)
# -----------------------------------------------------
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_FILE="${SCRIPT_DIR}/sync_config.sh"
LOCKFILE="${SCRIPT_DIR}/.sync.lock"
LOGFILE="${SCRIPT_DIR}/cron_sync.log"
MAX_RUNTIME=3600  # Maximum runtime in seconds (1 hour)
PYTHON_CMD="python3"  # Default Python command
MAX_LOG_SIZE=10485760  # 10MB in bytes
MAX_LOG_FILES=5  # Maximum number of rotated log files to keep
VERBOSE=false

# Load config file if it exists
if [ -f "${CONFIG_FILE}" ]; then
    source "${CONFIG_FILE}"
fi

# -----------------------------------------------------
# Functions
# -----------------------------------------------------
# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current timestamp
get_timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(get_timestamp)
    local color=""
    
    case "$level" in
        "INFO") color="${GREEN}" ;;
        "WARNING") color="${YELLOW}" ;;
        "ERROR") color="${RED}" ;;
        *) color="${BLUE}" ;;
    esac
    
    echo -e "[${timestamp}] ${color}${level}${NC}: ${message}" | tee -a "${LOGFILE}"
    
    # Check if log rotation is needed
    if [ -f "${LOGFILE}" ] && [ $(stat -f%z "${LOGFILE}" 2>/dev/null || stat -c%s "${LOGFILE}") -gt ${MAX_LOG_SIZE} ]; then
        rotate_logs
    fi
}

# Rotate log files
rotate_logs() {
    log "INFO" "Rotating log files" > /dev/null  # Don't log to the file being rotated
    
    # Remove the oldest log if it exists
    if [ -f "${LOGFILE}.${MAX_LOG_FILES}" ]; then
        rm "${LOGFILE}.${MAX_LOG_FILES}"
    fi
    
    # Shift all existing logs
    for (( i=${MAX_LOG_FILES}-1; i>=1; i-- )); do
        j=$((i+1))
        if [ -f "${LOGFILE}.${i}" ]; then
            mv "${LOGFILE}.${i}" "${LOGFILE}.${j}"
        fi
    done
    
    # Move current log
    mv "${LOGFILE}" "${LOGFILE}.1"
    
    # Create new empty log file
    touch "${LOGFILE}"
}

# Clean up function
cleanup() {
    log "INFO" "Cleaning up..."
    # Remove lock file when script exits
    if [ -f "${LOCKFILE}" ]; then
        rm "${LOCKFILE}"
    fi
    if [ -f "${LOCKFILE}.time" ]; then
        rm "${LOCKFILE}.time"
    fi
    log "INFO" "Finished execution"
    log "INFO" "----------------------------------------"
}

# Check if process is running
is_process_running() {
    local pid=$1
    # Works on both Linux and macOS
    ps -p $pid > /dev/null 2>&1
    return $?
}

# Check dependencies
check_dependencies() {
    # Check if required commands are available
    for cmd in python3 date ps stat; do
        if ! command -v $cmd &> /dev/null; then
            log "ERROR" "Required command '$cmd' not found"
            exit 1
        fi
    done
}

# Show help
show_help() {
    echo "Usage: $0 [options] [-- args_for_data_sync]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message and exit"
    echo "  -v, --verbose  Enable verbose output"
    echo "  -f, --force    Force run even if another instance is running"
    echo "  -i, --init     Initialize data storage structure"
    echo
    echo "Any arguments after -- will be passed to data_sync.py"
    exit 0
}

# Set up trap for cleanup on script exit
trap cleanup EXIT INT TERM

# -----------------------------------------------------
# Process command line arguments
# -----------------------------------------------------
FORCE_RUN=false
ARGS_FOR_SCRIPT=""
PARSING_SCRIPT_ARGS=false
INIT_MODE=false

while [[ $# -gt 0 ]]; do
    if $PARSING_SCRIPT_ARGS; then
        ARGS_FOR_SCRIPT="$ARGS_FOR_SCRIPT $1"
        shift
        continue
    fi
    
    case $1 in
        -h|--help)
            show_help
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--force)
            FORCE_RUN=true
            shift
            ;;
        -i|--init)
            INIT_MODE=true
            ARGS_FOR_SCRIPT="$ARGS_FOR_SCRIPT --init"
            shift
            ;;
        --)
            PARSING_SCRIPT_ARGS=true
            shift
            ;;
        *)
            ARGS_FOR_SCRIPT="$ARGS_FOR_SCRIPT $1"
            shift
            ;;
    esac
done

# -----------------------------------------------------
# Prevent multiple instances
# -----------------------------------------------------
if [ -f "${LOCKFILE}" ] && [ "$FORCE_RUN" != "true" ]; then
    pid=$(cat ${LOCKFILE})
    if is_process_running $pid; then
        log "WARNING" "Another sync process is already running (PID: $pid)"
        
        # Check if it's been running too long (potentially stuck)
        if [ -f "${LOCKFILE}.time" ]; then
            start_time=$(cat "${LOCKFILE}.time")
            current_time=$(date +%s)
            runtime=$((current_time - start_time))
            
            if [ $runtime -gt $MAX_RUNTIME ]; then
                log "WARNING" "Previous process exceeded maximum runtime (${MAX_RUNTIME}s). Force continuing."
            else
                log "INFO" "Exiting to avoid conflicts. Use -f to force run."
                exit 0
            fi
        else
            log "INFO" "Exiting to avoid conflicts. Use -f to force run."
            exit 0
        fi
    else
        log "INFO" "Found stale lock file. Removing."
    fi
fi

# Create lock file with current PID
echo $$ > "${LOCKFILE}"
# Store start time
date +%s > "${LOCKFILE}.time"

# -----------------------------------------------------
# Script start
# -----------------------------------------------------
log "INFO" "----------------------------------------"
log "INFO" "Starting Growatt data synchronization"

# Check for required commands
check_dependencies

if $VERBOSE; then
    log "INFO" "Running in verbose mode"
    log "INFO" "Using script directory: ${SCRIPT_DIR}"
    log "INFO" "Using log file: ${LOGFILE}"
fi

# Trim leading/trailing spaces from arguments
ARGS_FOR_SCRIPT=$(echo "$ARGS_FOR_SCRIPT" | xargs)

if [ -n "$ARGS_FOR_SCRIPT" ]; then
    log "INFO" "Custom arguments provided: $ARGS_FOR_SCRIPT"
fi

# Change to the script directory
cd "${SCRIPT_DIR}" || {
    log "ERROR" "Failed to change to script directory: ${SCRIPT_DIR}"
    exit 1
}

# Set up environment variables
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Try to use virtual environment if available
VENV_PATHS=("${SCRIPT_DIR}/venv" "${SCRIPT_DIR}/.venv" "${SCRIPT_DIR}/../venv" "${SCRIPT_DIR}/../.venv")
for venv_path in "${VENV_PATHS[@]}"; do
    if [ -d "$venv_path" ] && [ -f "$venv_path/bin/python" ]; then
        log "INFO" "Using virtual environment at: $venv_path"
        source "$venv_path/bin/activate"
        PYTHON_CMD="$venv_path/bin/python"
        break
    fi
done

# Verify Python command is available
if ! command -v $PYTHON_CMD &> /dev/null; then
    log "ERROR" "Python command not found: $PYTHON_CMD"
    exit 1
fi

# Show Python version if verbose
if $VERBOSE; then
    PYTHON_VERSION=$($PYTHON_CMD --version)
    log "INFO" "Using Python: $PYTHON_VERSION"
fi

# Check if the data_sync.py file exists
if [ ! -f "${SCRIPT_DIR}/data_sync.py" ]; then
    log "ERROR" "data_sync.py not found in ${SCRIPT_DIR}"
    exit 1
fi

# Run the data sync script with any provided arguments
script_start_time=$(date +%s)
log "INFO" "Executing data_sync.py ${ARGS_FOR_SCRIPT}"

if $VERBOSE; then
    $PYTHON_CMD "${SCRIPT_DIR}/data_sync.py" $ARGS_FOR_SCRIPT 2>&1 | tee -a "${LOGFILE}"
    EXIT_CODE=${PIPESTATUS[0]}
else
    $PYTHON_CMD "${SCRIPT_DIR}/data_sync.py" $ARGS_FOR_SCRIPT >> "${LOGFILE}" 2>&1
    EXIT_CODE=$?
fi

script_end_time=$(date +%s)
runtime=$((script_end_time - script_start_time))

# Report status
if [ $EXIT_CODE -eq 0 ]; then
    log "INFO" "Data sync completed successfully in ${runtime} seconds"
else
    log "ERROR" "Data sync failed with exit code ${EXIT_CODE} after ${runtime} seconds"
fi

exit $EXIT_CODE
