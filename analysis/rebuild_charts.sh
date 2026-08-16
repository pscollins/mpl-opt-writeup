#!/bin/bash
#
# Regenerate charts and standalone PDF
set -e

source env/bin/activate
python3 ./build_charts.py --config=config.json

CHARTS_DIR="charts"
TARGET_PDF="${CHARTS_DIR}/all_charts.pdf"

if [ -f "$TARGET_PDF" ]; then
    max_n=0
    for f in "${CHARTS_DIR}"/all_charts.old*.pdf; do
        [ -e "$f" ] || continue
        num=$(basename "$f" | sed -n 's/^all_charts\.old\([0-9]\+\)\.pdf$/\1/p')
        if [ -n "$num" ] && [ "$num" -gt "$max_n" ]; then
            max_n=$num
        fi
    done
    next_n=$((max_n + 1))
    echo "Archiving previous ${TARGET_PDF} to ${CHARTS_DIR}/all_charts.old${next_n}.pdf"
    mv "$TARGET_PDF" "${CHARTS_DIR}/all_charts.old${next_n}.pdf"
fi

make -C "${CHARTS_DIR}"
