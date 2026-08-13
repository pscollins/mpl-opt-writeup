#!/bin/bash
set -e

source ./chameleon_env.sh
source ./env/bin/activate

DURATION="2h"

# Parse arguments if provided
for i in "$@"; do
  case $i in
    --duration=*)
      DURATION="${i#*=}"
      shift
      ;;
  esac
done

TIME_OFFSET=$(echo "$DURATION" | sed -E 's/([0-9]+)d/\1 days /g; s/([0-9]+)h/\1 hours /g; s/([0-9]+)m/\1 minutes /g')
END_DATE=$(date -u -d "now + $TIME_OFFSET" +"%Y-%m-%d %H:%M")

NODE_TYPES=(
  "compute_zen3"
  "compute_icelake_r750"
  "compute_icelake_r650"
  "compute_skylake"
  "compute_haswell"
  "compute_cascadelake_r640"
  "gpu_p100"
  "gpu_a100"
)

echo "=========================================================="
echo " Checking Host Capacity for Duration: $DURATION"
echo " Target End Date (UTC): $END_DATE"
echo "=========================================================="
printf "%-25s | %-15s\n" "NODE TYPE" "STATUS"
echo "----------------------------------------------------------"

for nt in "${NODE_TYPES[@]}"; do
  LEASE_NAME="check_cap_${nt}_$$"
  
  # Try creating a test lease
  if openstack reservation lease create \
      --reservation min=1,max=1,resource_type=physical:host,resource_properties="[\"==\", \"\$node_type\", \"$nt\"]" \
      --end-date "$END_DATE" \
      "$LEASE_NAME" >/dev/null 2>&1; then
      
    printf "%-25s | \033[0;32mAVAILABLE\033[0m\n" "$nt"
    # Immediately delete the test lease
    openstack reservation lease delete "$LEASE_NAME" >/dev/null 2>&1 || true
  else
    printf "%-25s | \033[0;31mUNAVAILABLE\033[0m\n" "$nt"
  fi
done

echo "=========================================================="
