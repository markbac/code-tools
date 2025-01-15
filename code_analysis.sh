#!/bin/bash

# Script: code_analysis.sh
# Description: Runs Splint, Clang-Tidy, and Flawfinder on C code files with options for recursive scanning, output files, and custom settings.
# Usage: ./code_analysis.sh [OPTIONS] <file_or_directory>

# Default settings
C_STANDARD="c11"
SPLINT_OUTPUT="splint_output.txt"
CLANG_TIDY_OUTPUT="clang_tidy_output.txt"
FLAWFINDER_OUTPUT="flawfinder_output.txt"

# Function to display help
show_help() {
    echo "Usage: $0 [OPTIONS] <file_or_directory>"
    echo ""
    echo "Options:"
    echo "  -s <standard>    Set the C standard (default: c11)"
    echo "  -o <file>        Set output file for Splint results (default: splint_output.txt)"
    echo "  -t <file>        Set output file for Clang-Tidy results (default: clang_tidy_output.txt)"
    echo "  -f <file>        Set output file for Flawfinder results (default: flawfinder_output.txt)"
    echo "  -h               Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -s c99 -o splint.txt -t clang_tidy.txt -f flawfinder.txt path/to/code"
    exit 0
}

# Parse command-line arguments
while getopts ":s:o:t:f:h" opt; do
    case $opt in
        s) C_STANDARD="$OPTARG" ;;
        o) SPLINT_OUTPUT="$OPTARG" ;;
        t) CLANG_TIDY_OUTPUT="$OPTARG" ;;
        f) FLAWFINDER_OUTPUT="$OPTARG" ;;
        h) show_help ;;
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done
shift $((OPTIND - 1))

# Ensure a target file or directory is provided
if [ -z "$1" ]; then
    echo "Error: No target file or directory specified."
    echo "Use -h for help."
    exit 1
fi

TARGET="$1"

# Function to check and install missing tools
check_and_install_tools() {
    local tool=$1
    if ! command -v "$tool" &> /dev/null; then
        echo "$tool not found. Attempting to install..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y "$tool"
        elif command -v yum &> /dev/null; then
            sudo yum install -y "$tool"
        elif command -v brew &> /dev/null; then
            brew install "$tool"
        else
            echo "Error: Package manager not found. Please install $tool manually."
            exit 1
        fi
    fi
}

# Check and install required tools
check_and_install_tools "splint"
check_and_install_tools "clang-tidy"
check_and_install_tools "flawfinder"

# Function to gather all include directories
get_include_dirs() {
    find "$1" -type d
}

# Gather include directories
INCLUDE_DIRS=$(get_include_dirs "$TARGET")
INCLUDE_FLAGS=""
for dir in $INCLUDE_DIRS; do
    INCLUDE_FLAGS="$INCLUDE_FLAGS -I$dir"
done

# Function to run Splint
run_splint() {
    echo "Running Splint..."
    if [ -d "$TARGET" ]; then
        find "$TARGET" -name "*.c" -exec splint $INCLUDE_FLAGS {} \; > "$SPLINT_OUTPUT" 2>&1
    else
        splint $INCLUDE_FLAGS "$TARGET" > "$SPLINT_OUTPUT" 2>&1
    fi
    echo "Splint analysis completed. Results saved to $SPLINT_OUTPUT."
}

# Function to run Clang-Tidy
run_clang_tidy() {
    echo "Running Clang-Tidy..."
    if [ -d "$TARGET" ]; then
        find "$TARGET" -name "*.c" -exec clang-tidy {} -- -std=$C_STANDARD $INCLUDE_FLAGS \; > "$CLANG_TIDY_OUTPUT" 2>&1
    else
        clang-tidy "$TARGET" -- -std=$C_STANDARD $INCLUDE_FLAGS > "$CLANG_TIDY_OUTPUT" 2>&1
    fi
    echo "Clang-Tidy analysis completed. Results saved to $CLANG_TIDY_OUTPUT."
}

# Function to run Flawfinder
run_flawfinder() {
    echo "Running Flawfinder..."
    if [ -d "$TARGET" ]; then
        flawfinder "$TARGET" > "$FLAWFINDER_OUTPUT" 2>&1
    else
        flawfinder "$TARGET" > "$FLAWFINDER_OUTPUT" 2>&1
    fi
    echo "Flawfinder analysis completed. Results saved to $FLAWFINDER_OUTPUT."
}

# Run the tools
run_splint
run_clang_tidy
run_flawfinder

echo "Code analysis completed. All results are saved to the respective output files."
