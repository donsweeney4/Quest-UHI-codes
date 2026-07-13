#!/bin/bash

# Path to the log file
LOG_FILE_1="/home/uhi/ProcessSensorPushData.log"

# Number of lines to display from the end of each file
myLINES=10

# Function to print the tail of a log file
print_tail() {
    local file=$1
    local lines=$2
    echo ""
    echo "Showing last $lines lines of $file"
    echo "---------------------------------"
    tail -n $myLINES $file
    echo ""
}

# Print the tail of the log file
print_tail $LOG_FILE_1 $myLINES