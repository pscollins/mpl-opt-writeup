#!/bin/bash
#
# Regenerate charts and standalone PDF
set -e

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-0}"

source env/bin/activate
python3 ./build_charts.py --config=config.json

CHARTS_DIR="charts"
TARGET_PDF="${CHARTS_DIR}/all_charts.pdf"
TEMP_PREV=""

if [ -f "$TARGET_PDF" ]; then
    TEMP_PREV=$(mktemp "${CHARTS_DIR}/all_charts.prev.XXXXXX.pdf")
    cp "$TARGET_PDF" "$TEMP_PREV"
fi

trap 'if [ -n "$TEMP_PREV" ] && [ -f "$TEMP_PREV" ]; then rm -f "$TEMP_PREV"; fi' EXIT

make -C "${CHARTS_DIR}"

if [ -n "$TEMP_PREV" ] && [ -f "$TEMP_PREV" ]; then
    if ! cmp -s "$TEMP_PREV" "$TARGET_PDF"; then
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
        mv "$TEMP_PREV" "${CHARTS_DIR}/all_charts.old${next_n}.pdf"
    else
        echo "No changes in ${TARGET_PDF}; skipping backup."
        rm -f "$TEMP_PREV"
    fi
fi

