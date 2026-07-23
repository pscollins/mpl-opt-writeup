#!/bin/bash
set -e
set -x

# Setup to configure the reserved instance after running ./reserve_machine.sh
INSTANCE_NAME=flattening_tests
KEY_NAME=mpl-testing

# Grab the ID for the common `sharednet1`
SHAREDNET1_ID=$(openstack network show sharednet1 -f json | jq -r '.id')
# Grab the ID for our specific lease
RESERVATION_ID=$(openstack reservation lease show $INSTANCE_NAME -c reservations -f json | jq -r '.reservations[0].id')

openstack server create \
          --image CC-Ubuntu26.04 \
          --flavor baremetal \
          --key-name $KEY_NAME \
          --nic net-id=$SHAREDNET1_ID \
          --hint reservation=$RESERVATION_ID \
          $INSTANCE_NAME

