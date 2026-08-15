#!/bin/bash
#
# Trivial wrapper to regenerate charts
source env/bin/activate
python3 ./build_charts.py --config=config.json
