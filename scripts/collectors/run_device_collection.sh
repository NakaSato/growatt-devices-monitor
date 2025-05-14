#!/bin/bash
# run_device_collection.sh - Script to run device collection and export data

# Set default values
ACTION="collect"
OUTPUT_DIR="data/devices"
DEBUG=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --action)
      ACTION="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Create timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/devices_${TIMESTAMP}.json"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
mkdir -p logs

# Set Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Setup logging level
if [ "$DEBUG" = true ]; then
  export DEBUG=true
  echo "Debug mode enabled"
fi

# Run appropriate action
case $ACTION in
  collect)
    echo "Running devices collection..."
    python scripts/collectors/collect_devices_data.py collect
    
    echo "Exporting collected data to $OUTPUT_FILE"
    python scripts/collectors/collect_devices_data.py export --output "$OUTPUT_FILE"
    
    echo "Device collection and export completed"
    ;;
    
  export-only)
    echo "Running export-only mode..."
    echo "Exporting database data to $OUTPUT_FILE"
    python scripts/collectors/collect_devices_data.py export --output "$OUTPUT_FILE"
    
    echo "Device export completed"
    ;;
    
  get-device)
    if [ -z "$DEVICE_ID" ]; then
      echo "Error: DEVICE_ID is required for get-device action"
      exit 1
    fi
    
    echo "Getting device details for ID: $DEVICE_ID"
    DEVICE_OUTPUT="${OUTPUT_DIR}/device_${DEVICE_ID}_${TIMESTAMP}.json"
    
    python scripts/collectors/collect_devices_data.py get "$DEVICE_ID" --json | tee "$DEVICE_OUTPUT"
    
    echo "Device details saved to $DEVICE_OUTPUT"
    ;;
    
  *)
    echo "Unknown action: $ACTION"
    echo "Available actions: collect, export-only, get-device"
    exit 1
    ;;
esac

# List the output files
echo "Generated files in $OUTPUT_DIR:"
ls -la "$OUTPUT_DIR"

exit 0
