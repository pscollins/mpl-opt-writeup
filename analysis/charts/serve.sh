#!/bin/bash

# Simple script to serve output files on GCP VM
#  To use:
#   ./serve.sh
#   http://34.136.76.137:8080/solution.pdf
python3 -m http.server 8080
