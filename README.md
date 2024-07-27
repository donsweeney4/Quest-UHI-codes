# Quest-UHI-codes

Misc. collection of codes, mostly python, to process urban heat island data

# Mobile sensor processing:

* process_and_plot.py:  First draft of code that reads an input file exported from the mobile sensors and plots the route on google maps.

# Stationary SensorPush sensor processing

* ProcessIncomingMailAttachments_1: Code on AWS EC2 instance.  Moves incoming mail with attached .zip data file from SensorPush and places the attachment in a file

* UnZipToCSV_2.py:  Code on AWS EC2 instance.  Unzips the file and places the resulting .csv in a file

* ProcessCSVtoSQL_3.py: Code on AWS EC2 instance Moves through the .csv file and writes data into mySQL database.  Moves the .csv file into an archive.

