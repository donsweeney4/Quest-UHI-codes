#!/bin/bash

# Paths to the log files
LOG_FILE_1="/home/uhi/logs/ProcessIncomingMailAttachments_1.log"
LOG_FILE_2="/home/uhi/logs/UnZipToCSV_2.log"
LOG_FILE_3="/home/uhi/logs/ProcessCSVtoSQL_3.log"

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

# Print the tail of each log file
print_tail $LOG_FILE_1 $myLINES
print_tail $LOG_FILE_2 $myLINES
print_tail $LOG_FILE_3 $myLINES