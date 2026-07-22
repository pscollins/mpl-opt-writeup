#!/bin/bash

# Ensure script exits if a command fails
set -e

DURATION=""

# Parse command line arguments
for i in "$@"; do
  case $i in
    --duration=*)
      DURATION="${i#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $i"
      echo "Usage: ./reserve_machine.sh --duration=<time>"
      exit 1
      ;;
  esac
done

# Validate duration was provided
if [ -z "$DURATION" ]; then
  echo "Error: --duration is required."
  echo "Examples: --duration=5h, --duration=1d, --duration=1d5h30m"
  exit 1
fi

# Convert shorthand (d, h, m) to GNU date friendly strings
# Example: "1d5h30m" becomes "1 days 5 hours 30 minutes "
TIME_OFFSET=$(echo "$DURATION" | sed -E 's/([0-9]+)d/\1 days /g; s/([0-9]+)h/\1 hours /g; s/([0-9]+)m/\1 minutes /g')

# Calculate exact timestamps in YYYY-MM-DD HH:MM format
START_DATE=$(date +"%Y-%m-%d %H:%M")
END_DATE=$(date -d "now + $TIME_OFFSET" +"%Y-%m-%d %H:%M")

echo "Requesting reservation..."
echo "Start: $START_DATE"
echo "End:   $END_DATE"
echo "---------------------------"

# Execute the OpenStack command
openstack reservation lease create \
  --reservation min=1,max=1,resource_type=physical:host,resource_properties='["=", "$node_type", "compute_skylake"]' \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  test
