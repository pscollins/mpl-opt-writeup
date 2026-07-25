#!/bin/bash

# Ensure script exits if a command fails
set -e

INSTANCE_NAME="flattening_tests"

source ./chameleon_env.sh
source ./env/bin/activate

echo "=========================================="
echo "Deleting OpenStack reserved resources"
echo "=========================================="

# 1. Delete Server Instance
echo "Checking for server '$INSTANCE_NAME'..."
if openstack server show "$INSTANCE_NAME" >/dev/null 2>&1; then
  echo "Deleting server '$INSTANCE_NAME'..."
  openstack server delete "$INSTANCE_NAME"
  echo "Waiting for server '$INSTANCE_NAME' to be deleted..."
  while openstack server show "$INSTANCE_NAME" >/dev/null 2>&1; do
    sleep 3
  done
  echo "Server '$INSTANCE_NAME' deleted successfully."
else
  echo "Server '$INSTANCE_NAME' not found or already deleted."
fi

# 2. Release / Delete Floating IPs
echo "Checking for floating IPs..."
FLOATING_IPS=$(openstack floating ip list -c ID -f value 2>/dev/null || true)
if [ -n "$FLOATING_IPS" ]; then
  for IP_ID in $FLOATING_IPS; do
    if [ -n "$IP_ID" ]; then
      echo "Deleting floating IP '$IP_ID'..."
      openstack floating ip delete "$IP_ID" || true
    fi
  done
  echo "Floating IPs cleaned up."
else
  echo "No floating IPs found."
fi

# 3. Delete Reservation Lease
echo "Checking for reservation lease '$INSTANCE_NAME'..."
if openstack reservation lease show "$INSTANCE_NAME" >/dev/null 2>&1; then
  echo "Deleting reservation lease '$INSTANCE_NAME'..."
  openstack reservation lease delete "$INSTANCE_NAME"
  echo "Reservation lease '$INSTANCE_NAME' deleted successfully."
else
  echo "Reservation lease '$INSTANCE_NAME' not found or already deleted."
fi

echo "=========================================="
echo "All reserved resources deleted."
echo "=========================================="
