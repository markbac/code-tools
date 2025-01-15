#!/bin/bash

# Script: run_jscpd.sh
# Description: Runs jscpd on C code with configurable options for thresholds, paths, and logging, with increased memory limit.
# Usage: ./run_jscpd.sh [OPTIONS]

# Default settings
SCAN_PATH="."
THRESHOLD=5
OUTPUT_DIR="./report/"
FORMATS="c"

# Function to display help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -p <path>        Path to the directory or file to analyse (default: current directory)"
    echo "  -t <threshold>   Duplication threshold in percentage (default: 5)"
    echo "  -o <output>      Log output directory (default: ./report/)"
    echo "  -f <formats>     Code formats to scan (default: c)"
    echo "  -h               Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -p /path/to/code -t 10 -o ./output/ -f c,h"
    exit 0
}

# Parse command-line arguments
while getopts ":p:t:o:f:h" opt; do
    case $opt in
        p) SCAN_PATH="$OPTARG" ;;
        t) THRESHOLD="$OPTARG" ;;
        o) OUTPUT_DIR="$OPTARG" ;;
        f) FORMATS="$OPTARG" ;;
        h) show_help ;;
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

# Check if jscpd is installed
if ! command -v jscpd &>/dev/null; then
    echo "Error: jscpd is not installed. Install it using 'npm install -g jscpd'."
    exit 1
fi

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Set Node.js memory limit to 4 GB (adjust as needed)
export NODE_OPTIONS="--max-old-space-size=4096"

# Run jscpd
echo "Running jscpd on path: $SCAN_PATH"
echo "Threshold: $THRESHOLD%"
echo "Formats: $FORMATS"
echo "Logging to: $OUTPUT_DIR"

jscpd "$SCAN_PATH" \
    --min-tokens "$THRESHOLD" \
    --threshold "$THRESHOLD" \
    --reporters "console,html" \
    --output "$OUTPUT_DIR" \
    --format "$FORMATS"

echo "Analysis complete. Reports saved to $OUTPUT_DIR."
