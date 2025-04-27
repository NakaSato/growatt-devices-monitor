#!/bin/bash
# Example script showing how to run data_sync.py in different scenarios

# Set the base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$BASE_DIR" || { echo "Error changing to script directory"; exit 1; }

# Define color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Growatt API Data Sync Examples${NC}"
echo -e "${YELLOW}===========================${NC}"

# Function to show examples
show_example() {
    echo -e "\n${GREEN}$1${NC}"
    echo -e "${YELLOW}Command:${NC} $2"
    echo -e "${YELLOW}Description:${NC} $3"
    echo -e "${YELLOW}Example output:${NC}"
    echo "  $ $2"
    echo "  [Example output would appear here]"
    echo
}

# Display examples
show_example "First-time Setup" \
    "python3 data_sync.py --init" \
    "Initializes the data storage structure, creates config file, and sets up the database."

show_example "Regular Data Sync" \
    "python3 data_sync.py" \
    "Fetches data from Growatt API and stores it in the SQLite database."

show_example "Database Setup Only" \
    "python3 data_sync.py --setup-db" \
    "Sets up or resets just the database tables without changing other files."

show_example "Verbose Mode" \
    "python3 data_sync.py --verbose" \
    "Runs the sync with more detailed logging for troubleshooting."

show_example "Custom Data Directory" \
    "python3 data_sync.py --init --dir /path/to/custom/directory" \
    "Initializes data storage in a custom directory."

show_example "Using Run Sync Wrapper" \
    "./run_sync.sh" \
    "Uses the wrapper script for better logging and error handling."

show_example "Force Sync Even if Another is Running" \
    "./run_sync.sh -f" \
    "Forces sync even if another sync process is already running."

show_example "Initialize Using Wrapper" \
    "./run_sync.sh -i" \
    "Initializes data storage through the wrapper script."

# Ask if user wants to run an example
echo -e "${BLUE}Would you like to run one of these examples? (y/n)${NC}"
read -r answer

if [[ "$answer" == "y" ]]; then
    echo -e "${YELLOW}Enter the number of the example to run (1-8):${NC}"
    read -r example_num
    
    case $example_num in
        1) echo "Running: python3 data_sync.py --init"
           python3 data_sync.py --init ;;
        2) echo "Running: python3 data_sync.py"
           python3 data_sync.py ;;
        3) echo "Running: python3 data_sync.py --setup-db"
           python3 data_sync.py --setup-db ;;
        4) echo "Running: python3 data_sync.py --verbose"
           python3 data_sync.py --verbose ;;
        5) echo "Please customize the directory path before running"
           echo "python3 data_sync.py --init --dir /custom/path" ;;
        6) echo "Running: ./run_sync.sh"
           chmod +x run_sync.sh
           ./run_sync.sh ;;
        7) echo "Running: ./run_sync.sh -f"
           chmod +x run_sync.sh
           ./run_sync.sh -f ;;
        8) echo "Running: ./run_sync.sh -i"
           chmod +x run_sync.sh
           ./run_sync.sh -i ;;
        *) echo -e "${RED}Invalid selection${NC}" ;;
    esac
fi

echo -e "\n${BLUE}For more information, see the README.md${NC}"
