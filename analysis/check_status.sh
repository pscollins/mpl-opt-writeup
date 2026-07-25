#!/bin/bash

# Ensure script exits if a command fails
set -e

INSTANCE_NAME="flattening_tests"

source ./chameleon_env.sh
source ./env/bin/activate

echo "=========================================="
echo "OpenStack Resource Status: $INSTANCE_NAME"
echo "=========================================="

echo ""
echo "--- 1. Reservation Lease ---"
if openstack reservation lease show "$INSTANCE_NAME" >/dev/null 2>&1; then
  openstack reservation lease show "$INSTANCE_NAME" -f table
else
  echo "No reservation lease found with name '$INSTANCE_NAME'."
fi

echo ""
echo "--- 2. Server Instance ---"
if openstack server show "$INSTANCE_NAME" >/dev/null 2>&1; then
  openstack server show "$INSTANCE_NAME" -f table
else
  echo "No server instance found with name '$INSTANCE_NAME'."
fi

echo ""
echo "--- 3. Allocated Floating IPs ---"
openstack floating ip list -f table
